import io
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from starlette.requests import Request
from app.api import profile_videos as pv


def test_profile_and_magic():
    assert pv._profile("data-management") == "data-management"
    assert pv._profile("interior-business") == "interior-business"
    with pytest.raises(HTTPException) as exc: pv._profile("other")
    assert exc.value.status_code == 404
    assert pv._check_magic("video/mp4", b"\0\0\0\x18ftypisom")
    assert pv._check_magic("video/webm", b"\x1a\x45\xdf\xa3\x93")
    assert not pv._check_magic("video/mp4", b"bad")


def test_embed_parsing():
    assert pv._parse_embed("https://www.youtube.com/watch?v=abc123") == ("youtube", "abc123")
    assert pv._parse_embed("https://youtu.be/abc123") == ("youtube", "abc123")
    assert pv._parse_embed("https://vimeo.com/123456") == ("vimeo", "123456")
    assert pv._parse_embed("https://cdn.example.com/video.mp4") == ("direct", "https://cdn.example.com/video.mp4")
    with pytest.raises(HTTPException): pv._parse_embed("http://cdn.example.com/video.mp4")


def test_ranges():
    assert pv._range(None, 100) == (0, 99, False)
    assert pv._range("bytes=10-19", 100) == (10, 19, True)
    assert pv._range("bytes=10-", 100) == (10, 99, True)
    assert pv._range("bytes=-10", 100) == (90, 99, True)
    with pytest.raises(HTTPException) as exc: pv._range("bytes=100-110", 100)
    assert exc.value.status_code == 416
    assert exc.value.headers["Content-Range"] == "bytes */100"

class FakeObject:
    def __init__(self, data): self.s = io.BytesIO(data)
    def read(self, n=-1): return self.s.read(n)
    def close(self): pass
    def release_conn(self): pass


class FakeMinio:
    def __init__(self): self.objects = {}; self.calls = []
    def bucket_exists(self, bucket): return True
    def make_bucket(self, bucket): pass
    def stat_object(self, bucket, key): return SimpleNamespace(size=len(self.objects[(bucket, key)]))
    def get_object(self, bucket, key, offset=0, length=None):
        data = self.objects[(bucket, key)]
        return FakeObject(data[offset:offset + length if length is not None else None])
    def put_object(self, bucket, key, data, length, content_type=None):
        self.calls.append(("put", key)); self.objects[(bucket, key)] = data.read(length)
    def remove_object(self, bucket, key): self.calls.append(("remove", key)); self.objects.pop((bucket, key), None)
    def compose_object(self, bucket, key, parts):
        self.calls.append(("compose", key)); self.objects[(bucket, key)] = b"".join(self.objects[(p.bucket_name, p.object_name)] for p in parts)


class FakeSession:
    def __init__(self, values): self.values = values
    async def get(self, model, key): return self.values.get(key)


@pytest.mark.asyncio
async def test_stream_full_and_range(monkeypatch):
    fake = FakeMinio(); key = "profiles/data-management/v1.mp4"; payload = b"0123456789" * 100
    fake.objects[(pv.BUCKET, key)] = payload
    video = SimpleNamespace(id="v1", published=True, source_type="upload", object_key=key, content_type="video/mp4")
    monkeypatch.setattr(pv, "client", fake); session = FakeSession({"v1": video})
    req = Request({"type":"http", "method":"GET", "path":"/", "headers":[]})
    response = await pv.stream("v1", req, session); body = b"".join([c async for c in response.body_iterator])
    assert response.status_code == 200 and body == payload and response.headers["accept-ranges"] == "bytes"
    req = Request({"type":"http", "method":"GET", "path":"/", "headers":[(b"range", b"bytes=10-29")]})
    response = await pv.stream("v1", req, session); body = b"".join([c async for c in response.body_iterator])
    assert response.status_code == 206 and body == payload[10:30]
    assert response.headers["content-range"] == f"bytes 10-29/{len(payload)}"

@pytest.mark.asyncio
async def test_stream_hides_unpublished(monkeypatch):
    monkeypatch.setattr(pv, "client", FakeMinio())
    video = SimpleNamespace(published=False, source_type="upload", object_key="x", content_type="video/mp4")
    with pytest.raises(HTTPException) as exc:
        await pv.stream("v2", Request({"type":"http", "method":"GET", "path":"/", "headers":[]}), FakeSession({"v2": video}))
    assert exc.value.status_code == 404


def test_admin_role_detection():
    assert pv._admin_roles({"roles":["admin"]})
    assert pv._admin_roles({"roles":[], "realm_access":{"roles":["platform_admin"]}})
    assert not pv._admin_roles({"roles":["user"]})


@pytest.mark.asyncio
async def test_complete_single_part_uses_copy(monkeypatch):
    fake = FakeMinio(); monkeypatch.setattr(pv, "client", fake)
    upload_id = "u1"; key = pv._part_key(upload_id, 1); data = b"\0\0\0\x18ftyp" + b"x" * 100
    fake.objects[(pv.BUCKET, key)] = data
    upload = SimpleNamespace(id=upload_id, profile_slug="data-management", title="T", description=None, filename="a.mp4", content_type="video/mp4", size=len(data), total_parts=1, created_by="admin", created_at=pv.datetime.utcnow())
    class Session(FakeSession):
        def add(self, obj): self.video = obj
        async def delete(self, obj): pass
        async def commit(self): pass
        async def rollback(self): pass
    session = Session({upload_id: upload})
    result = await pv.complete_upload(upload_id, {"sub":"admin", "roles":["admin"]}, session)
    assert result["profile_slug"] == "data-management"
    assert any(c[0] == "put" for c in fake.calls)
    assert not any(c[0] == "compose" for c in fake.calls)
    assert not any(k[1].startswith("tmp/profile-videos/") for k in fake.objects)
