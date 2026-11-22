"""Only in-memory fake devices are used; no host disk is opened."""
import hashlib
import io
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/software-os-diagnostics"))
import usb_writer_core as writer


class FakeDevice:
    def __init__(self, **kw):
        self.path = kw.get("path", "/dev/fake-usb")
        self.stable_id = kw.get("stable_id", "FAKE-001")
        self.size_bytes = kw.get("size_bytes", 128)
        self.is_removable = kw.get("is_removable", True)
        self.is_system_disk = kw.get("is_system_disk", False)
        self.data = bytearray(self.size_bytes)
        self.flushed = False

    def write_at(self, offset, data):
        self.data[offset:offset + len(data)] = data
        return len(data)

    def read_at(self, offset, length):
        return bytes(self.data[offset:offset + length])

    def flush(self):
        self.flushed = True


class RewritingStream(io.BytesIO):
    """Changes its content if rewound, simulating a mutable image source."""
    def __init__(self, original, replacement):
        super().__init__(original)
        self.original = original
        self.replacement = replacement
        self.seek_count = 0

    def seek(self, *args):
        self.seek_count += 1
        if self.seek_count > 1:
            super().seek(0)
            super().truncate(0)
            super().write(self.replacement)
            super().seek(0)
            return super().seek(*args)
        return super().seek(*args)


class WriterTests(unittest.TestCase):
    def setUp(self):
        self.payload = b"simulated recovery image"
        self.digest = hashlib.sha256(self.payload).hexdigest()
        self.device = FakeDevice()
        self.identity = writer.identity_of(self.device)

    def run_write(self, **overrides):
        args = dict(
            image=io.BytesIO(self.payload),
            expected_size=len(self.payload),
            expected_sha256=self.digest,
            publisher_digest_url="https://vendor.example/SHA256SUMS",
            image_architecture="x86_64",
            target_architecture="x86_64",
            supported_architecture_pairs={("x86_64", "x86_64"), ("arm64", "arm64")},
            selected_identity=self.identity,
            current_device=lambda: self.device,
            open_device=lambda: self.device,
            typed_confirmation="ERASE /dev/fake-usb",
            chunk_size=5,
        )
        args.update(overrides)
        return writer.write_verified_image(**args)

    def test_success_writes_flushes_and_reads_back(self):
        result = self.run_write()
        self.assertTrue(result.verified)
        self.assertTrue(self.device.flushed)
        self.assertEqual(bytes(self.device.data[:len(self.payload)]), self.payload)

    def test_system_disk_refused(self):
        self.device.is_system_disk = True
        self.identity = writer.identity_of(self.device)
        with self.assertRaises(writer.WriterRefused):
            self.run_write()

    def test_non_removable_refused(self):
        self.device.is_removable = False
        self.identity = writer.identity_of(self.device)
        with self.assertRaises(writer.WriterRefused):
            self.run_write()

    def test_wrong_confirmation_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(typed_confirmation="ERASE")

    def test_insufficient_capacity_refused(self):
        self.device.size_bytes = 2
        self.identity = writer.identity_of(self.device)
        with self.assertRaises(writer.WriterRefused):
            self.run_write()

    def test_changed_identity_refused_before_open(self):
        other = FakeDevice(stable_id="OTHER")
        opened = []
        with self.assertRaises(writer.WriterRefused):
            self.run_write(
                current_device=lambda: other,
                open_device=lambda: opened.append(1) or self.device,
            )
        self.assertEqual(opened, [])

    def test_digest_mismatch_refused_before_open(self):
        opened = []
        with self.assertRaises(writer.WriterRefused):
            self.run_write(
                expected_sha256="0" * 64,
                open_device=lambda: opened.append(1) or self.device,
            )
        self.assertEqual(opened, [])

    def test_non_https_source_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(publisher_digest_url="http://vendor.example/hash")

    def test_https_url_with_embedded_credentials_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(publisher_digest_url="https://user:pass@vendor.example/hash")

    def test_malformed_https_port_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(publisher_digest_url="https://vendor.example:not-a-port/hash")

    def test_cancelled_never_returns_success(self):
        with self.assertRaises(writer.WriteCancelled):
            self.run_write(cancel_requested=lambda: True)

    def test_cancelled_after_final_chunk_before_flush_is_not_success(self):
        # Five write chunks complete; the sixth check is immediately before flush.
        checks = iter([False, False, False, False, False, True])
        with self.assertRaises(writer.WriteCancelled):
            self.run_write(cancel_requested=lambda: next(checks))
        self.assertEqual(bytes(self.device.data[:len(self.payload)]), self.payload)
        self.assertFalse(self.device.flushed)

    def test_declared_size_mismatch_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(expected_size=len(self.payload) + 1)

    def test_oversized_image_refused_before_open(self):
        opened = []
        with self.assertRaises(writer.WriterRefused):
            self.run_write(
                expected_size=len(self.payload) - 1,
                open_device=lambda: opened.append(1) or self.device,
            )
        self.assertEqual(opened, [])
        self.assertEqual(bytes(self.device.data), bytes(self.device.size_bytes))

    def test_boolean_size_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(expected_size=True)

    def test_boolean_chunk_size_refused(self):
        with self.assertRaises(writer.WriterRefused):
            self.run_write(chunk_size=True)

    def test_mutating_source_cannot_change_staged_bytes(self):
        replacement = b"ATTACKER-CONTENT-CHANGED"
        source = RewritingStream(self.payload, replacement)
        result = self.run_write(image=source)
        self.assertEqual(result.sha256, self.digest)
        self.assertEqual(bytes(self.device.data[:len(self.payload)]), self.payload)
        self.assertEqual(source.seek_count, 1)

    def test_partial_write_failure_is_not_success(self):
        def broken_write(offset, data):
            if offset >= 5:
                raise OSError("simulated media error")
            self.device.data[offset:offset + 2] = data[:2]
            return 2
        self.device.write_at = broken_write
        with self.assertRaises(OSError):
            self.run_write()

    def test_permission_error_is_not_success(self):
        def denied_write(offset, data):
            raise PermissionError("simulated permission denied")
        self.device.write_at = denied_write
        with self.assertRaises(PermissionError):
            self.run_write()

    def test_readback_mismatch_is_not_success(self):
        original_read = self.device.read_at

        def corrupted_read(offset, length):
            chunk = original_read(offset, length)
            return (bytes([chunk[0] ^ 1]) + chunk[1:]) if offset == 0 and chunk else chunk

        self.device.read_at = corrupted_read
        with self.assertRaisesRegex(IOError, "Post-write read-back verification failed"):
            self.run_write()

    def test_opened_device_identity_mismatch_is_refused(self):
        other = FakeDevice(stable_id="REPLACED")
        with self.assertRaises(writer.WriterRefused):
            self.run_write(open_device=lambda: other)

    def test_cancellation_after_progress_is_not_success(self):
        checks = iter([False, False, True])
        progress = []
        with self.assertRaises(writer.WriteCancelled):
            self.run_write(
                cancel_requested=lambda: next(checks),
                progress=lambda done, total: progress.append(done),
            )
        self.assertTrue(progress)

    def test_unsupported_architecture_pair_refused_before_open(self):
        opened = []
        with self.assertRaises(writer.WriterRefused):
            self.run_write(
                image_architecture="arm64",
                target_architecture="x86_64",
                open_device=lambda: opened.append(1) or self.device,
            )
        self.assertEqual(opened, [])

    def test_missing_architecture_matrix_refused_before_open(self):
        opened = []
        with self.assertRaises(writer.WriterRefused):
            self.run_write(
                supported_architecture_pairs=set(),
                open_device=lambda: opened.append(1) or self.device,
            )
        self.assertEqual(opened, [])

    def test_malformed_architecture_matrix_refused_before_open(self):
        opened = []
        with self.assertRaises(writer.WriterRefused):
            self.run_write(
                supported_architecture_pairs={("x86_64",)},
                open_device=lambda: opened.append(1) or self.device,
            )
        self.assertEqual(opened, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
