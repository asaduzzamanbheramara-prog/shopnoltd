"""Fail-closed USB writer core. No OS discovery or physical-device adapter is included."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from typing import BinaryIO, Callable, Protocol, Collection
from urllib.parse import urlparse

class WriterRefused(RuntimeError): pass
class WriteCancelled(RuntimeError): pass

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
    return DeviceIdentity(device.path, device.stable_id, device.size_bytes,
                          device.is_removable, device.is_system_disk)

def validate_architecture_pair(image_architecture: str, target_architecture: str,
                               supported_pairs: Collection[tuple[str, str]]) -> None:
    """Require an exact pair from a caller-supplied, reviewed compatibility matrix."""
    image_arch = image_architecture.strip().casefold()
    target_arch = target_architecture.strip().casefold()
    allowed = {(image.strip().casefold(), target.strip().casefold())
               for image, target in supported_pairs}
    if not image_arch or not target_arch or not allowed:
        raise WriterRefused("A reviewed image/target architecture matrix is required.")
    if (image_arch, target_arch) not in allowed:
        raise WriterRefused("Unsupported image and target architecture combination.")

def _hash_image(image: BinaryIO, size: int, chunk_size: int) -> str:
    digest, total = hashlib.sha256(), 0
    image.seek(0)
    while True:
        chunk = image.read(chunk_size)
        if not chunk: break
        total += len(chunk)
        digest.update(chunk)
    image.seek(0)
    if total != size: raise WriterRefused("Image size does not match declared size.")
    return digest.hexdigest()

def _write_all(device: BlockDevice, offset: int, data: bytes) -> None:
    done = 0
    while done < len(data):
        count = device.write_at(offset + done, data[done:])
        if isinstance(count, bool) or not isinstance(count, int) or count <= 0 or count > len(data) - done:
            raise IOError("Invalid or failed block-device write.")
        done += count

def write_verified_image(*, image: BinaryIO, expected_size: int,
    expected_sha256: str, publisher_digest_url: str,
    image_architecture: str, target_architecture: str,
    supported_architecture_pairs: Collection[tuple[str, str]],
    selected_identity: DeviceIdentity, current_device: Callable[[], BlockDevice],
    open_device: Callable[[], BlockDevice], typed_confirmation: str,
    cancel_requested: Callable[[], bool] = lambda: False,
    progress: Callable[[int, int], None] = lambda _done, _total: None,
    chunk_size: int = 1024 * 1024) -> WriteResult:
    """Core only; a separately reviewed native adapter is still required."""
    validate_architecture_pair(image_architecture, target_architecture, supported_architecture_pairs)
    parsed = urlparse(publisher_digest_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise WriterRefused("Publisher digest source must be HTTPS.")
    if expected_size <= 0 or chunk_size <= 0:
        raise WriterRefused("Image size and chunk size must be positive.")
    if len(expected_sha256) != 64 or any(c not in "0123456789abcdefABCDEF" for c in expected_sha256):
        raise WriterRefused("A publisher-sourced SHA-256 digest is required.")
    selected = selected_identity
    if not selected.path or not selected.stable_id:
        raise WriterRefused("Stable device path and identity are required.")
    if selected.is_system_disk or not selected.is_removable:
        raise WriterRefused("Target is not an eligible removable device.")
    if selected.size_bytes < expected_size:
        raise WriterRefused("Target capacity is insufficient.")
    if typed_confirmation != "ERASE " + selected.path:
        raise WriterRefused("Exact-target destructive confirmation did not match.")
    digest = _hash_image(image, expected_size, chunk_size)
    if digest.casefold() != expected_sha256.casefold():
        raise WriterRefused("Image does not match publisher-provided SHA-256.")
    if identity_of(current_device()) != selected:
        raise WriterRefused("Device identity changed; rescan and confirm again.")
    device = open_device()
    if identity_of(device) != selected:
        raise WriterRefused("Opened device differs from confirmed device.")
    image.seek(0)
    offset = 0
    while True:
        if cancel_requested():
            raise WriteCancelled("Cancelled; media may be partial and must not be booted.")
        chunk = image.read(chunk_size)
        if not chunk: break
        _write_all(device, offset, chunk)
        offset += len(chunk)
        progress(offset, expected_size)
    if offset != expected_size: raise IOError("Image stream ended early.")
    device.flush()
    readback, offset = hashlib.sha256(), 0
    while offset < expected_size:
        length = min(chunk_size, expected_size - offset)
        chunk = device.read_at(offset, length)
        if len(chunk) != length: raise IOError("Read-back was incomplete.")
        readback.update(chunk)
        offset += length
    if readback.hexdigest().casefold() != digest.casefold():
        raise IOError("Post-write read-back verification failed.")
    return WriteResult(expected_size, digest, True)
