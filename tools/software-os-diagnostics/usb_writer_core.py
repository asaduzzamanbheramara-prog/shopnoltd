"""Fail-closed USB writer core. No OS discovery or physical-device adapter is included."""
from __future__ import annotations

import hashlib
import tempfile
from dataclasses import dataclass
from typing import BinaryIO, Callable, Protocol, Collection
from urllib.parse import urlparse


class WriterRefused(RuntimeError):
    pass


class WriteCancelled(RuntimeError):
    pass


class BlockDevice(Protocol):
    path: str
    stable_id: str
    size_bytes: int
    is_removable: bool
    is_system_disk: bool

    def write_at(self, offset: int, data: bytes) -> int: ...
    def read_at(self, offset: int, length: int) -> bytes: ...
    def flush(self) -> None: ...


@dataclass(frozen=True)
class DeviceIdentity:
    path: str
    stable_id: str
    size_bytes: int
    is_removable: bool
    is_system_disk: bool


@dataclass(frozen=True)
class WriteResult:
    bytes_written: int
    sha256: str
    verified: bool


def identity_of(device: BlockDevice) -> DeviceIdentity:
    return DeviceIdentity(
        device.path, device.stable_id, device.size_bytes,
        device.is_removable, device.is_system_disk
    )


def validate_architecture_pair(
    image_architecture: str,
    target_architecture: str,
    supported_pairs: Collection[tuple[str, str]],
) -> None:
    """Require an exact pair from a caller-supplied, reviewed compatibility matrix."""
    if not isinstance(image_architecture, str) or not isinstance(target_architecture, str):
        raise WriterRefused("Image and target architectures must be explicit strings.")
    image_arch = image_architecture.strip().casefold()
    target_arch = target_architecture.strip().casefold()
    try:
        pairs = list(supported_pairs)
        allowed = set()
        for pair in pairs:
            if not isinstance(pair, (tuple, list)) or len(pair) != 2:
                raise WriterRefused("Architecture matrix entries must be exact pairs.")
            image, target = pair
            if not isinstance(image, str) or not isinstance(target, str):
                raise WriterRefused("Architecture matrix values must be strings.")
            allowed.add((image.strip().casefold(), target.strip().casefold()))
    except TypeError as exc:
        raise WriterRefused("A reviewed architecture compatibility matrix is required.") from exc
    if not image_arch or not target_arch or not allowed:
        raise WriterRefused("A reviewed image/target architecture matrix is required.")
    if (image_arch, target_arch) not in allowed:
        raise WriterRefused("Unsupported image and target architecture combination.")


def _stage_and_verify_image(
    image: BinaryIO, expected_size: int, expected_sha256: str, chunk_size: int
):
    """Copy bounded source bytes to a private spool and verify before any device is opened."""
    staged = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    digest = hashlib.sha256()
    total = 0
    try:
        image.seek(0)
        while total <= expected_size:
            request_size = min(chunk_size, expected_size - total + 1)
            chunk = image.read(request_size)
            if not isinstance(chunk, bytes):
                raise WriterRefused("Image source must provide binary bytes.")
            if not chunk:
                break
            if len(chunk) > request_size or total + len(chunk) > expected_size:
                raise WriterRefused("Image exceeds its declared size.")
            staged.write(chunk)
            digest.update(chunk)
            total += len(chunk)
        if total != expected_size:
            raise WriterRefused("Image size does not match declared size.")
        actual = digest.hexdigest()
        if actual.casefold() != expected_sha256.casefold():
            raise WriterRefused("Image does not match publisher-provided SHA-256.")
        staged.seek(0)
        return staged, actual
    except Exception:
        staged.close()
        raise


def _write_all(device: BlockDevice, offset: int, data: bytes) -> None:
    done = 0
    while done < len(data):
        count = device.write_at(offset + done, data[done:])
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0 or count > len(data) - done:
            raise IOError("Invalid or failed block-device write.")
        done += count


def write_verified_image(
    *,
    image: BinaryIO,
    expected_size: int,
    expected_sha256: str,
    publisher_digest_url: str,
    image_architecture: str,
    target_architecture: str,
    supported_architecture_pairs: Collection[tuple[str, str]],
    selected_identity: DeviceIdentity,
    current_device: Callable[[], BlockDevice],
    open_device: Callable[[], BlockDevice],
    typed_confirmation: str,
    cancel_requested: Callable[[], bool] = lambda: False,
    progress: Callable[[int, int], None] = lambda _done, _total: None,
    chunk_size: int = 1024 * 1024,
) -> WriteResult:
    """Core only; a separately reviewed native adapter is still required."""
    validate_architecture_pair(
        image_architecture, target_architecture, supported_architecture_pairs
    )

    if not isinstance(publisher_digest_url, str):
        raise WriterRefused("A publisher digest source URL is required.")
    try:
        parsed = urlparse(publisher_digest_url)
        valid_https_source = (
            parsed.scheme.casefold() == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and not parsed.fragment
        )
        # Accessing .port also rejects malformed port syntax.
        _ = parsed.port
    except ValueError as exc:
        raise WriterRefused("Publisher digest source URL is invalid.") from exc
    if not valid_https_source:
        raise WriterRefused("Publisher digest source must be a valid HTTPS URL without credentials or fragment.")

    if isinstance(expected_size, bool) or not isinstance(expected_size, int) or expected_size <= 0:
        raise WriterRefused("Image size must be a positive integer.")
    if isinstance(chunk_size, bool) or not isinstance(chunk_size, int) or chunk_size <= 0:
        raise WriterRefused("Chunk size must be a positive integer.")
    if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(
        c not in "0123456789abcdefABCDEF" for c in expected_sha256
    ):
        raise WriterRefused("A publisher-sourced SHA-256 digest is required.")
    if not isinstance(selected_identity, DeviceIdentity):
        raise WriterRefused("A previously scanned device identity is required.")
    selected = selected_identity
    if (
        not isinstance(selected.path, str) or not selected.path.strip()
        or not isinstance(selected.stable_id, str) or not selected.stable_id.strip()
    ):
        raise WriterRefused("Stable device path and identity are required.")
    if isinstance(selected.size_bytes, bool) or not isinstance(selected.size_bytes, int) or selected.size_bytes <= 0:
        raise WriterRefused("Target capacity must be a positive integer.")
    if not isinstance(selected.is_removable, bool) or not isinstance(selected.is_system_disk, bool):
        raise WriterRefused("Device removable/system-disk flags must be explicit booleans.")
    if selected.is_system_disk or not selected.is_removable:
        raise WriterRefused("Target is not an eligible removable device.")
    if selected.size_bytes < expected_size:
        raise WriterRefused("Target capacity is insufficient.")
    if typed_confirmation != "ERASE " + selected.path:
        raise WriterRefused("Exact-target destructive confirmation did not match.")

    # Stage and verify a stable byte sequence before acquiring any destructive handle.
    staged, digest = _stage_and_verify_image(image, expected_size, expected_sha256, chunk_size)
    try:
        if identity_of(current_device()) != selected:
            raise WriterRefused("Device identity changed; rescan and confirm again.")
        device = open_device()
        if identity_of(device) != selected:
            raise WriterRefused("Opened device differs from confirmed device.")

        staged.seek(0)
        offset = 0
        write_digest = hashlib.sha256()
        while offset < expected_size:
            if cancel_requested():
                raise WriteCancelled("Cancelled; media may be partial and must not be booted.")
            chunk = staged.read(min(chunk_size, expected_size - offset))
            if not isinstance(chunk, bytes) or not chunk:
                raise IOError("Staged image ended unexpectedly.")
            if offset + len(chunk) > expected_size:
                raise IOError("Staged image exceeded the confirmed write length.")
            _write_all(device, offset, chunk)
            write_digest.update(chunk)
            offset += len(chunk)
            progress(offset, expected_size)

        if offset != expected_size or write_digest.hexdigest().casefold() != digest.casefold():
            raise IOError("Written image stream did not match the verified staged image.")
        if cancel_requested():
            raise WriteCancelled("Cancelled before flush/verification; media must not be booted.")
        device.flush()

        readback, offset = hashlib.sha256(), 0
        while offset < expected_size:
            length = min(chunk_size, expected_size - offset)
            chunk = device.read_at(offset, length)
            if not isinstance(chunk, bytes) or len(chunk) != length:
                raise IOError("Read-back was incomplete.")
            readback.update(chunk)
            offset += length
        if readback.hexdigest().casefold() != digest.casefold():
            raise IOError("Post-write read-back verification failed.")
        return WriteResult(expected_size, digest, True)
    finally:
        staged.close()
