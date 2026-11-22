"""Only an in-memory fake device is used; no host disk is opened."""
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
        self.path=kw.get("path","/dev/fake-usb"); self.stable_id=kw.get("stable_id","FAKE-001")
        self.size_bytes=kw.get("size_bytes",128); self.is_removable=kw.get("is_removable",True)
        self.is_system_disk=kw.get("is_system_disk",False); self.data=bytearray(self.size_bytes)
        self.flushed=False
    def write_at(self, offset, data):
        self.data[offset:offset+len(data)]=data
        return len(data)
    def read_at(self, offset, length): return bytes(self.data[offset:offset+length])
    def flush(self): self.flushed=True

class WriterTests(unittest.TestCase):
    def setUp(self):
        self.payload=b"simulated recovery image"; self.digest=hashlib.sha256(self.payload).hexdigest()
        self.device=FakeDevice(); self.identity=writer.identity_of(self.device)
    def run_write(self, **overrides):
        args=dict(image=io.BytesIO(self.payload), expected_size=len(self.payload),
            expected_sha256=self.digest, publisher_digest_url="https://vendor.example/SHA256SUMS",
            selected_identity=self.identity, current_device=lambda:self.device,
            open_device=lambda:self.device, typed_confirmation="ERASE /dev/fake-usb", chunk_size=5)
        args.update(overrides)
        return writer.write_verified_image(**args)
    def test_success_writes_flushes_and_reads_back(self):
        result=self.run_write()
        self.assertTrue(result.verified); self.assertTrue(self.device.flushed)
        self.assertEqual(bytes(self.device.data[:len(self.payload)]),self.payload)
    def test_system_disk_refused(self):
        self.device.is_system_disk=True; self.identity=writer.identity_of(self.device)
        with self.assertRaises(writer.WriterRefused): self.run_write()
    def test_non_removable_refused(self):
        self.device.is_removable=False; self.identity=writer.identity_of(self.device)
        with self.assertRaises(writer.WriterRefused): self.run_write()
    def test_wrong_confirmation_refused(self):
        with self.assertRaises(writer.WriterRefused): self.run_write(typed_confirmation="ERASE")
    def test_insufficient_capacity_refused(self):
        self.device.size_bytes=2; self.identity=writer.identity_of(self.device)
        with self.assertRaises(writer.WriterRefused): self.run_write()
    def test_changed_identity_refused_before_open(self):
        other=FakeDevice(stable_id="OTHER"); opened=[]
        with self.assertRaises(writer.WriterRefused):
            self.run_write(current_device=lambda:other,open_device=lambda:opened.append(1) or self.device)
        self.assertEqual(opened,[])
    def test_digest_mismatch_refused_before_open(self):
        opened=[]
        with self.assertRaises(writer.WriterRefused):
            self.run_write(expected_sha256="0"*64,open_device=lambda:opened.append(1) or self.device)
        self.assertEqual(opened,[])
    def test_non_https_source_refused(self):
        with self.assertRaises(writer.WriterRefused): self.run_write(publisher_digest_url="http://vendor.example/hash")
    def test_cancelled_never_returns_success(self):
        with self.assertRaises(writer.WriteCancelled): self.run_write(cancel_requested=lambda:True)
    def test_declared_size_mismatch_refused(self):
        with self.assertRaises(writer.WriterRefused): self.run_write(expected_size=len(self.payload)+1)

if __name__=="__main__": unittest.main(verbosity=2)
