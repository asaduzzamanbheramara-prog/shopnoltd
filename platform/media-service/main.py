"""Shopnoltd media service: image edit/convert, design render, video jobs.

Internal only (ClusterIP + NetworkPolicy). Every caller has its own bearer token:
MEDIA_SERVICE_TOKENS="ai-platform:<secret>,code-server:<secret>".
The ai-platform caller may pass X-Owner (the signed-in user id); other callers are
their own owner. Jobs can only be read by the owner that created them.
"""
import asyncio
import hmac
import io
import json
import os
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

Image.MAX_IMAGE_PIXELS = 50_000_000  # refuse decompression bombs

DATA = Path(os.getenv("DATA_DIR", "/data"))
DATA.mkdir(parents=True, exist_ok=True)
MAX_IMAGE = int(os.getenv("MAX_IMAGE_MB", "25")) << 20
MAX_VIDEO = int(os.getenv("MAX_VIDEO_MB", "200")) << 20
MAX_JOB_SECONDS = int(os.getenv("MAX_JOB_SECONDS", "600"))
MAX_INPUT_SECONDS = int(os.getenv("MAX_INPUT_SECONDS", "1800"))
TTL = int(os.getenv("JOB_TTL_SECONDS", "3600"))
MAX_PENDING = int(os.getenv("MAX_PENDING_JOBS", "5"))
MAX_SIDE = 8000

TOKENS = {}
for _item in os.environ["MEDIA_SERVICE_TOKENS"].split(","):  # missing env = crash on start (fail closed)
    _name, _, _secret = _item.strip().partition(":")
    if _name and _secret:
        TOKENS[_name] = _secret
if not TOKENS:
    raise RuntimeError("MEDIA_SERVICE_TOKENS has no valid name:secret entries")

jobs: dict = {}
tasks: set = set()
video_sem = asyncio.Semaphore(1)   # one ffmpeg at a time on this small node
render_sem = asyncio.Semaphore(2)


def caller(authorization: str = Header(""), x_owner: str = Header("")) -> str:
    scheme, _, presented = authorization.partition(" ")
    if scheme == "Bearer":
        for name, secret in TOKENS.items():
            if hmac.compare_digest(presented.encode(), secret.encode()):
                return (x_owner.strip()[:64] or name) if name == "ai-platform" else name
    raise HTTPException(401, "unauthorized")


async def janitor():
    while True:
        await asyncio.sleep(300)
        now = time.time()
        for jid, j in list(jobs.items()):
            if now - j["created"] > TTL and j["status"] not in ("queued", "running"):
                shutil.rmtree(DATA / jid, ignore_errors=True)
                jobs.pop(jid, None)
        for d in DATA.iterdir():  # leftovers from a restart
            if d.is_dir() and d.name not in jobs and now - d.stat().st_mtime > TTL:
                shutil.rmtree(d, ignore_errors=True)


@asynccontextmanager
async def lifespan(_app):
    t = asyncio.create_task(janitor())
    yield
    t.cancel()


app = FastAPI(title="shopno media service", lifespan=lifespan)


@app.get("/healthz")
def healthz():
    return {"ok": True}


# ---------- helpers ----------
def num(value, name, lo=None, hi=None):
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise HTTPException(400, f"{name} must be a number")
    if lo is not None and v < lo:
        raise HTTPException(400, f"{name} must be at least {lo}")
    if hi is not None and v > hi:
        raise HTTPException(400, f"{name} must be at most {hi}")
    return v


async def save_upload(up: UploadFile, dest: Path, limit: int):
    size = 0
    with dest.open("wb") as f:
        while chunk := await up.read(1 << 20):
            size += len(chunk)
            if size > limit:
                f.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(413, f"file is larger than {limit >> 20} MB")
            f.write(chunk)
    if size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, "empty file")


def clean_stem(name, default="file"):
    stem = Path(name or default).stem
    stem = "".join(c for c in stem if c.isprintable() and c not in '\\/:*?"<>|')[:80]
    return stem.strip() or default


def attachment(body: bytes, mime: str, stem: str, ext: str) -> Response:
    stem = clean_stem(stem)
    ascii_name = "".join(c if (c.isascii() and c.isalnum()) or c in "-_." else "_" for c in stem) or "file"
    disposition = f"attachment; filename=\"{ascii_name}.{ext}\"; filename*=UTF-8''{quote(stem + '.' + ext)}"
    return Response(body, media_type=mime, headers={"Content-Disposition": disposition})


# ---------- images ----------
FORMATS = {
    "jpg": ("JPEG", "image/jpeg", "jpg"),
    "jpeg": ("JPEG", "image/jpeg", "jpg"),
    "png": ("PNG", "image/png", "png"),
    "webp": ("WEBP", "image/webp", "webp"),
}


def hex_rgb(value):
    s = str(value).lstrip("#")
    try:
        if len(s) != 6:
            raise ValueError
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        raise HTTPException(400, "background must look like #ffffff")


def adjust(im, ops):
    alpha = im.getchannel("A") if im.mode == "RGBA" else None
    rgb = im.convert("RGB")
    if ops.get("auto_fix"):
        rgb = ImageOps.autocontrast(rgb, cutoff=1)
        rgb = rgb.filter(ImageFilter.UnsharpMask(radius=1.2, percent=60, threshold=3))
    for key, cls in (("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast),
                     ("saturation", ImageEnhance.Color), ("sharpness", ImageEnhance.Sharpness)):
        if ops.get(key) is not None:
            rgb = cls(rgb).enhance(num(ops[key], key, 0, 3))
    if ops.get("grayscale"):
        rgb = ImageOps.grayscale(rgb).convert("RGB")
    if alpha is not None:
        rgb.putalpha(alpha)
    return rgb


def process_image(data: bytes, ops: dict):
    fmt = str(ops.get("format", "jpg")).lower()
    if fmt not in FORMATS:
        raise HTTPException(400, "format must be jpg, png or webp")
    pil_name, mime, ext = FORMATS[fmt]
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise HTTPException(400, "not a readable image")
    im = ImageOps.exif_transpose(im)
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA" if ("A" in im.getbands() or "transparency" in im.info) else "RGB")

    if ops.get("crop"):
        try:
            left, top, right, bottom = [int(v) for v in ops["crop"]]
        except (TypeError, ValueError):
            raise HTTPException(400, "crop must be [left, top, right, bottom] in pixels")
        box = (max(0, left), max(0, top), min(im.width, right), min(im.height, bottom))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise HTTPException(400, "crop box is empty")
        im = im.crop(box)
    if ops.get("rotate"):
        im = im.rotate(-num(ops["rotate"], "rotate"), expand=True)  # degrees clockwise
    if ops.get("flip") == "h":
        im = ImageOps.mirror(im)
    elif ops.get("flip") == "v":
        im = ImageOps.flip(im)

    w = int(num(ops["width"], "width", 1, MAX_SIDE)) if ops.get("width") else None
    h = int(num(ops["height"], "height", 1, MAX_SIDE)) if ops.get("height") else None
    if w and h:
        im = ImageOps.contain(im, (w, h), Image.LANCZOS)  # keeps the aspect ratio
    elif w or h:
        ratio = (w / im.width) if w else (h / im.height)
        im = im.resize((max(1, round(im.width * ratio)), max(1, round(im.height * ratio))), Image.LANCZOS)

    im = adjust(im, ops)

    if pil_name == "JPEG" and im.mode == "RGBA":  # JPG has no transparency: flatten onto a color
        flat = Image.new("RGB", im.size, hex_rgb(ops.get("background", "#ffffff")))
        flat.paste(im, mask=im.getchannel("A"))
        im = flat

    quality = int(num(ops.get("quality", 92), "quality", 1, 100))
    kwargs = {}
    if pil_name == "JPEG":
        kwargs = {"quality": quality, "optimize": True, "progressive": True}
    elif pil_name == "WEBP":
        kwargs = {"quality": quality}
    else:
        kwargs = {"optimize": True}
    out = io.BytesIO()
    im.save(out, pil_name, **kwargs)
    return out.getvalue(), mime, ext


@app.post("/v1/image/edit", dependencies=[Depends(caller)])
async def image_edit(file: UploadFile = File(...), ops: str = Form("{}")):
    try:
        o = json.loads(ops)
    except json.JSONDecodeError:
        raise HTTPException(400, "ops must be JSON")
    if not isinstance(o, dict):
        raise HTTPException(400, "ops must be a JSON object")
    tmp = DATA / f"img-{uuid.uuid4().hex}"
    try:
        await save_upload(file, tmp, MAX_IMAGE)
        data = tmp.read_bytes()
    finally:
        tmp.unlink(missing_ok=True)
    async with render_sem:
        body, mime, ext = await asyncio.to_thread(process_image, data, o)
    return attachment(body, mime, file.filename, ext)


# ---------- designs (SVG and HTML) ----------
def svg_render(src: str, fmt: str, width, height, background):
    import cairosvg  # safe mode is the default: no external files, no entities
    kw = {"bytestring": src.encode()}
    if width:
        kw["output_width"] = int(num(width, "width", 1, MAX_SIDE))
    if height:
        kw["output_height"] = int(num(height, "height", 1, MAX_SIDE))
    if fmt == "pdf":
        return cairosvg.svg2pdf(**kw), "application/pdf", "pdf"
    png = cairosvg.svg2png(**kw)
    if fmt == "png":
        return png, "image/png", "png"
    return process_image(png, {"format": fmt, "background": background})


def html_to_pdf(src: str):
    from weasyprint import HTML

    try:  # WeasyPrint 66+: only inline data: URLs may load, nothing from the network or disk
        from weasyprint import URLFetcher
        fetcher = URLFetcher(allowed_protocols=["data"])
    except ImportError:  # older WeasyPrint releases
        from weasyprint import default_url_fetcher

        def fetcher(url, *a, **k):
            if url.startswith("data:"):
                return default_url_fetcher(url, *a, **k)
            raise ValueError("external resources are blocked")

    return HTML(string=src, url_fetcher=fetcher).write_pdf(), "application/pdf", "pdf"


@app.post("/v1/design/render", dependencies=[Depends(caller)])
async def design_render(req: dict):
    kind = str(req.get("kind", ""))
    fmt = str(req.get("format", "png")).lower()
    src = req.get("source")
    if not isinstance(src, str) or not src.strip():
        raise HTTPException(400, "source is required")
    if len(src) > 2_000_000:
        raise HTTPException(413, "source is larger than 2 MB")
    if kind == "svg" and fmt in ("png", "jpg", "jpeg", "webp", "pdf"):
        job = (svg_render, src, fmt, req.get("width"), req.get("height"), req.get("background", "#ffffff"))
    elif kind == "html" and fmt == "pdf":
        job = (html_to_pdf, src)
    else:
        raise HTTPException(400, "supported: svg -> png/jpg/webp/pdf, html -> pdf")
    try:
        async with render_sem:
            body, mime, ext = await asyncio.to_thread(*job)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(422, f"could not render this design: {str(e)[:200]}")
    return attachment(body, mime, req.get("name") or "design", ext)


# ---------- video jobs ----------
VIDEO_OPS = {"transcode", "trim", "resize", "thumbnail", "gif", "audio", "mute"}
ALLOWED_CONTAINERS = {"mov", "mp4", "matroska", "webm", "avi", "gif"}  # blocks playlists like hls/concat


async def probe(path: Path) -> float:
    p = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", str(path),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, _ = await asyncio.wait_for(p.communicate(), 20)
    except asyncio.TimeoutError:
        p.kill()
        raise HTTPException(400, "could not read this video in time")
    if p.returncode:
        raise HTTPException(400, "not a readable video")
    fmt = json.loads(out).get("format", {})
    if not set(str(fmt.get("format_name", "")).split(",")) & ALLOWED_CONTAINERS:
        raise HTTPException(400, "unsupported video container (use mp4, mov, webm, mkv, avi or gif)")
    duration = float(fmt.get("duration") or 0)
    if duration > MAX_INPUT_SECONDS:
        raise HTTPException(400, f"video is longer than {MAX_INPUT_SECONDS // 60} minutes")
    return duration


def build_cmd(op: str, p: dict, src: Path, d: Path, duration: float = 0.0):
    base = ["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y",
            "-protocol_whitelist", "file", "-threads", "2"]
    crf = str(int(num(p.get("crf", 23), "crf", 18, 35)))
    x264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", crf, "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-movflags", "+faststart"]
    s = str(src)

    def inside(value, name):  # ffmpeg silently writes an empty file when you seek past the end
        if duration and value >= duration:
            raise HTTPException(400, f"{name} ({value:g}s) is after the end of the video ({duration:.1f}s)")
        return value

    if op == "transcode":
        fmt = str(p.get("format", "mp4")).lower()
        if fmt == "webm":
            out, mime = d / "out.webm", "video/webm"
            enc = ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", crf, "-row-mt", "1", "-c:a", "libopus"]
        elif fmt == "mp4":
            out, mime, enc = d / "out.mp4", "video/mp4", x264
        else:
            raise HTTPException(400, "format must be mp4 or webm")
        cmd = base + ["-i", s] + enc + [str(out)]
    elif op == "trim":
        start = inside(num(p.get("start", 0), "start", 0), "start")
        pre = ["-ss", f"{start}"]
        if p.get("end") is not None:
            end = num(p["end"], "end", 0)
            if end <= start:
                raise HTTPException(400, "end must be after start")
            pre += ["-t", f"{end - start}"]
        out, mime = d / "out.mp4", "video/mp4"
        cmd = base + pre + ["-i", s] + x264 + [str(out)]
    elif op == "resize":
        w = int(num(p.get("width"), "width", 64, 3840)) // 2 * 2
        out, mime = d / "out.mp4", "video/mp4"
        cmd = base + ["-i", s, "-vf", f"scale={w}:-2"] + x264 + [str(out)]
    elif op == "mute":
        out, mime = d / "out.mp4", "video/mp4"
        cmd = base + ["-i", s, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", crf,
                      "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)]
    elif op == "thumbnail":
        at = inside(num(p.get("at", 1), "at", 0), "at")
        out, mime = d / "out.jpg", "image/jpeg"
        cmd = base + ["-ss", f"{at}", "-i", s, "-frames:v", "1", "-q:v", "2", str(out)]
    elif op == "gif":
        width = int(num(p.get("width", 480), "width", 64, 1280))
        secs = num(p.get("seconds", 8), "seconds", 1, 15)
        start = inside(num(p.get("start", 0), "start", 0), "start")
        out, mime = d / "out.gif", "image/gif"
        vf = (f"fps=12,scale={width}:-1:flags=lanczos,split[a][b];"
              "[a]palettegen[p];[b][p]paletteuse")
        cmd = base + ["-ss", f"{start}", "-t", f"{secs}", "-i", s, "-vf", vf, str(out)]
    else:  # audio
        out, mime = d / "out.mp3", "audio/mpeg"
        cmd = base + ["-i", s, "-vn", "-c:a", "libmp3lame", "-q:a", "2", str(out)]
    return cmd, out, mime


async def run_job(job_id: str, cmd: list):
    job = jobs[job_id]
    async with video_sem:
        job["status"] = "running"
        proc = None
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
            _, err = await asyncio.wait_for(proc.communicate(), MAX_JOB_SECONDS)
            if proc.returncode or not job["out"].exists():
                job.update(status="failed", error=(err or b"").decode(errors="replace")[-300:] or "ffmpeg failed")
            else:
                job["status"] = "done"
        except asyncio.TimeoutError:
            if proc:
                proc.kill()
                await proc.wait()
            job.update(status="failed", error=f"timed out after {MAX_JOB_SECONDS} seconds")
        except Exception as e:
            job.update(status="failed", error=str(e)[:200])


@app.post("/v1/video/jobs", status_code=202)
async def video_create(file: UploadFile = File(...), op: str = Form(...), params: str = Form("{}"),
                       owner: str = Depends(caller)):
    if op not in VIDEO_OPS:
        raise HTTPException(400, f"op must be one of {sorted(VIDEO_OPS)}")
    try:
        p = json.loads(params)
    except json.JSONDecodeError:
        raise HTTPException(400, "params must be JSON")
    if not isinstance(p, dict):
        raise HTTPException(400, "params must be a JSON object")
    if sum(j["status"] in ("queued", "running") for j in jobs.values()) >= MAX_PENDING:
        raise HTTPException(429, "too many jobs running, try again in a minute")
    job_id = uuid.uuid4().hex
    d = DATA / job_id
    d.mkdir()
    src = d / "input"
    try:
        await save_upload(file, src, MAX_VIDEO)
        duration = await probe(src)
        cmd, out, mime = build_cmd(op, p, src, d, duration)
    except BaseException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    jobs[job_id] = {"owner": owner, "status": "queued", "error": None, "created": time.time(), "out": out,
                    "mime": mime, "download_name": f"{clean_stem(file.filename, 'video')}{out.suffix}"}
    t = asyncio.create_task(run_job(job_id, cmd))
    tasks.add(t)
    t.add_done_callback(tasks.discard)
    return {"job_id": job_id, "status": "queued"}


def get_job(job_id: str, owner: str) -> dict:
    j = jobs.get(job_id)
    if not j or j["owner"] != owner:
        raise HTTPException(404, "job not found")
    return j


@app.get("/v1/jobs/{job_id}")
def job_status(job_id: str, owner: str = Depends(caller)):
    j = get_job(job_id, owner)
    return {"job_id": job_id, "status": j["status"], "error": j["error"]}


@app.get("/v1/jobs/{job_id}/download")
def job_download(job_id: str, owner: str = Depends(caller)):
    j = get_job(job_id, owner)
    if j["status"] != "done":
        raise HTTPException(409, f"job is {j['status']}")
    return FileResponse(j["out"], media_type=j["mime"], filename=j["download_name"])
