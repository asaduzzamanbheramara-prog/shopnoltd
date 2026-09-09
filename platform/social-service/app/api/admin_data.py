"""Guarded data control-plane for BlogPost entities."""
import csv
import io
import json
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.blog import can_manage_blog, current_user
from app.core.db import Base, SessionLocal
from app.models.models import BlogPost

router = APIRouter()
MAX_ROWS = 5000
MAX_BYTES = 10 * 1024 * 1024


async def db():
    async with SessionLocal() as s:
        yield s


def _is_global(user: dict) -> bool:
    return bool(set(user.get("roles", [])) & {"admin", "platform_admin"})


def _scope(user: dict):
    if _is_global(user):
        return None
    return BlogPost.tenant_id == user.get("tenant_id", "default")


def _value(v):
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    return v


def _row(post: BlogPost) -> dict:
    return {c.name: _value(getattr(post, c.name)) for c in BlogPost.__table__.columns}


def _audit_table():
    return Base.metadata.tables.get("blog_admin_audit")


async def _audit(s: AsyncSession, user: dict, action: str, operation: str, before, after):
    table = _audit_table()
    if table is None:
        raise HTTPException(503, "blog_admin_audit table is not available")
    await s.execute(table.insert().values(
        id=str(uuid.uuid4()), actor_id=user.get("sub", "unknown"),
        tenant_id=user.get("tenant_id", "default"), action=action,
        operation=operation, before_json=json.dumps(before, default=str) if before is not None else None,
        after_json=json.dumps(after, default=str) if after is not None else None,
        created_at=datetime.utcnow(),
    ))


def _clean(payload: dict, *, partial=False):
    allowed = {"id", "title", "slug", "excerpt", "content", "cover_image", "status"}
    unknown = set(payload) - allowed
    if unknown:
        raise HTTPException(400, f"Unknown field(s): {', '.join(sorted(unknown))}")
    if not partial and not payload.get("title"):
        raise HTTPException(400, "title is required")
    if not partial and not payload.get("content"):
        raise HTTPException(400, "content is required")
    status = payload.get("status", "draft")
    if status not in {"draft", "published"}:
        raise HTTPException(400, "status must be draft or published")
    return {k: v for k, v in payload.items() if k in allowed and k != "id"}


def _parse_upload(filename: str, raw: bytes):
    lower = filename.lower()
    if lower.endswith(".json"):
        parsed = json.loads(raw.decode("utf-8-sig"))
        return parsed if isinstance(parsed, list) else parsed.get("rows", parsed.get("data", []))
    if lower.endswith(".csv"):
        return list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if lower.endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise HTTPException(503, "XLSX support is not installed") from exc
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        values = list(wb.active.values)
        if not values:
            return []
        headers = [str(x) if x is not None else "" for x in values[0]]
        return [dict(zip(headers, row)) for row in values[1:]]
    raise HTTPException(415, "Supported import formats: CSV, JSON, XLSX")


async def _match(s: AsyncSession, item: dict, user: dict):
    clauses = []
    if item.get("id"):
        clauses.append(BlogPost.id == str(item["id"]))
    if item.get("slug"):
        clauses.append(BlogPost.slug == str(item["slug"]))
    if not clauses:
        return None
    query = select(BlogPost).where(or_(*clauses))
    scope = _scope(user)
    if scope is not None:
        query = query.where(scope)
    return (await s.execute(query)).scalar_one_or_none()


def _prepare_insert(item: dict, user: dict):
    data = _clean(item)
    data["id"] = str(item.get("id") or uuid.uuid4())
    data["tenant_id"] = user.get("tenant_id", "default")
    data["author_id"] = user.get("sub", "unknown")
    data["published_at"] = datetime.utcnow() if data.get("status") == "published" else None
    return data


async def _plan(items, operation, user, s):
    if not items:
        raise HTTPException(400, "No rows supplied")
    if len(items) > MAX_ROWS:
        raise HTTPException(413, f"Maximum import size is {MAX_ROWS} rows")
    plan = []
    for raw in items:
        if not isinstance(raw, dict):
            raise HTTPException(400, "Every imported row must be an object")
        existing = await _match(s, raw, user)
        if operation == "add":
            if existing:
                raise HTTPException(409, "row already exists for supplied id/slug")
            action = "insert"
        elif operation in {"update", "merge", "replace"}:
            if not existing:
                raise HTTPException(404, "no matching row for supplied id/slug")
            action = "update"
        elif operation == "upsert":
            action = "update" if existing else "insert"
        elif operation == "delete":
            action = "delete" if existing else "skip"
        else:
            raise HTTPException(400, f"Unsupported operation: {operation}")
        data = _prepare_insert(raw, user) if action == "insert" else (_clean(raw, partial=True) if action == "update" else {})
        if action == "update" and not data:
            raise HTTPException(400, "update row contains no editable fields")
        plan.append((raw, existing, action, data))
    return plan


async def _read_rows(user, s):
    query = select(BlogPost).order_by(BlogPost.created_at.desc()).limit(MAX_ROWS)
    scope = _scope(user)
    if scope is not None:
        query = query.where(scope)
    return [_row(x) for x in (await s.execute(query)).scalars().all()]


@router.get("/schema")
async def schema(user=Depends(current_user)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    return {"entity": "blog_posts", "operations": ["check", "add", "add_below", "update", "replace", "upsert", "merge", "delete", "publish", "unpublish", "replace_rows", "export", "import"], "schema_replacement": False, "match_keys": ["id", "slug"], "fields": [c.name for c in BlogPost.__table__.columns], "tenant_scoped": True, "transactional": True}


@router.get("/analysis")
async def analysis(user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    q = select(BlogPost)
    scope = _scope(user)
    if scope is not None:
        q = q.where(scope)
    posts = (await s.execute(q)).scalars().all()
    status = {"draft": 0, "published": 0}
    for p in posts:
        status[p.status] = status.get(p.status, 0) + 1
    return {"rows": len(posts), "columns": len(BlogPost.__table__.columns), "status_distribution": status, "published_with_content": sum(1 for p in posts if p.status == "published" and p.content), "avg_title_length": round(sum(len(p.title) for p in posts) / len(posts), 2) if posts else 0, "visualization": {"recommended": "2d+3d", "dimensions": ["status", "created_at", "published_at"]}}


@router.get("/check")
async def check(user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    rows = await _read_rows(user, s)
    errors = []
    slugs = {}
    for item in rows:
        slug = item.get("slug")
        if not item.get("title") or not item.get("content"):
            errors.append({"id": item.get("id"), "error": "title/content is required"})
        if slug:
            if slug in slugs:
                errors.append({"id": item.get("id"), "error": f"duplicate slug: {slug}"})
            slugs[slug] = item.get("id")
        if item.get("status") == "published" and not item.get("published_at"):
            errors.append({"id": item.get("id"), "error": "published row has no published_at"})
    return {"ok": not errors, "rows_checked": len(rows), "errors": errors}


@router.post("/rows")
async def create_row(payload: dict, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    data = _prepare_insert(payload, user)
    existing = await _match(s, payload, user)
    if existing:
        raise HTTPException(409, "row already exists for supplied id/slug")
    post = BlogPost(**data)
    s.add(post)
    try:
        await s.flush()
        values = _row(post)
        await _audit(s, user, "create", "add", None, values)
        await s.commit()
        return values
    except HTTPException:
        await s.rollback(); raise
    except Exception as exc:
        await s.rollback(); raise HTTPException(409, f"Add failed: {exc}") from exc


@router.put("/rows/{record_id}")
async def update_row(record_id: str, payload: dict, replace: bool = False, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    query = select(BlogPost).where(BlogPost.id == record_id)
    scope = _scope(user)
    if scope is not None:
        query = query.where(scope)
    post = (await s.execute(query)).scalar_one_or_none()
    if post is None:
        raise HTTPException(404, "Record not found")
    before = _row(post)
    data = _clean(payload, partial=not replace)
    if replace:
        for field in ("title", "slug", "excerpt", "content", "cover_image", "status"):
            if field not in data:
                data[field] = None if field in {"excerpt", "cover_image"} else ("draft" if field == "status" else "")
    for key, value in data.items():
        setattr(post, key, value)
    if post.status == "published" and not post.published_at:
        post.published_at = datetime.utcnow()
    if post.status == "draft":
        post.published_at = None
    try:
        await s.flush(); after = _row(post); await _audit(s, user, "replace" if replace else "update", "replace" if replace else "update", before, after); await s.commit(); return after
    except HTTPException:
        await s.rollback(); raise
    except Exception as exc:
        await s.rollback(); raise HTTPException(409, f"Update failed: {exc}") from exc


@router.post("/rows/{record_id}/publish")
async def publish_row(record_id: str, published: bool = True, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    query = select(BlogPost).where(BlogPost.id == record_id)
    scope = _scope(user)
    if scope is not None:
        query = query.where(scope)
    post = (await s.execute(query)).scalar_one_or_none()
    if post is None:
        raise HTTPException(404, "Record not found")
    before = _row(post)
    post.status = "published" if published else "draft"
    post.published_at = datetime.utcnow() if published else None
    await s.flush(); after = _row(post); await _audit(s, user, "publish" if published else "unpublish", "publish", before, after); await s.commit()
    return after


@router.delete("/rows/{record_id}")
async def delete_row(record_id: str, confirm: bool = False, user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    if not confirm:
        raise HTTPException(400, "destructive delete requires confirm=true")
    query = select(BlogPost).where(BlogPost.id == record_id)
    scope = _scope(user)
    if scope is not None:
        query = query.where(scope)
    post = (await s.execute(query)).scalar_one_or_none()
    if post is None:
        raise HTTPException(404, "Record not found")
    before = _row(post); await s.delete(post); await _audit(s, user, "delete", "delete", before, None); await s.commit()
    return {"ok": True, "deleted": record_id}


@router.get("/export")
async def export_data(format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"), user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    rows = await _read_rows(user, s)
    fields = [c.name for c in BlogPost.__table__.columns]
    if format == "json":
        body = json.dumps({"entity": "blog_posts", "version": 1, "rows": rows}, indent=2).encode()
        return StreamingResponse(io.BytesIO(body), media_type="application/json", headers={"Content-Disposition": "attachment; filename=blog_posts.json"})
    if format == "csv":
        out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
        return StreamingResponse(io.BytesIO(out.getvalue().encode()), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=blog_posts.csv"})
    if format == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise HTTPException(503, "XLSX support is not installed") from exc
        wb = Workbook(); ws = wb.active; ws.title = "blog_posts"; ws.append(fields)
        for row in rows: ws.append([row.get(k) for k in fields])
        out = io.BytesIO(); wb.save(out); out.seek(0)
        return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=blog_posts.xlsx"})
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError as exc:
        raise HTTPException(503, "PDF reporting is not installed") from exc
    styles = getSampleStyleSheet(); out = io.BytesIO(); doc = SimpleDocTemplate(out, pagesize=A4)
    story = [Paragraph("Shopnoltd Blog Data Report", styles["Title"]), Spacer(1, 12), Paragraph(f"Rows: {len(rows)}", styles["BodyText"]), Paragraph(f"Generated: {datetime.utcnow().isoformat()}Z", styles["BodyText"])]
    doc.build(story); out.seek(0)
    return StreamingResponse(out, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=blog_posts.pdf"})


@router.post("/import/preview")
async def preview_import(operation: str = Query("add"), file: UploadFile = File(...), user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    if operation in {"create_table", "replace_schema"}:
        raise HTTPException(403, "Schema creation/replacement is not available for service-owned BlogPost schema")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, f"Maximum upload size is {MAX_BYTES} bytes")
    items = _parse_upload(file.filename or "import", raw)
    if operation == "replace_rows":
        if len(items) > MAX_ROWS:
            raise HTTPException(413, f"Maximum import size is {MAX_ROWS} rows")
        return {"operation": operation, "rows": len(items), "will_delete_existing": True, "preview": items[:20]}
    plan = await _plan(items, operation, user, s)
    return {"operation": operation, "rows": len(items), "counts": {"insert": sum(x[2] == "insert" for x in plan), "update": sum(x[2] == "update" for x in plan), "delete": sum(x[2] == "delete" for x in plan), "skip": sum(x[2] == "skip" for x in plan)}, "preview": [{"action": x[2], "row": x[0]} for x in plan[:20]]}


@router.post("/import")
async def commit_import(operation: str = Query("add"), confirm: bool = Query(False), file: UploadFile = File(...), user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    if operation in {"create_table", "replace_schema"}:
        raise HTTPException(403, "Schema creation/replacement is not available for service-owned BlogPost schema")
    if operation in {"delete", "replace_rows"} and not confirm:
        raise HTTPException(400, "destructive operation requires confirm=true")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, f"Maximum upload size is {MAX_BYTES} bytes")
    items = _parse_upload(file.filename or "import", raw)
    try:
        if operation == "replace_rows":
            stmt = delete(BlogPost); scope = _scope(user)
            if scope is not None: stmt = stmt.where(scope)
            result = await s.execute(stmt); deleted = result.rowcount or 0
            for item in items: s.add(BlogPost(**_prepare_insert(item, user)))
            await _audit(s, user, "replace_rows", operation, {"deleted": deleted}, {"inserted": len(items)})
            await s.commit(); return {"ok": True, "operation": operation, "deleted": deleted, "inserted": len(items)}
        plan = await _plan(items, operation, user, s); counts = {"insert": 0, "update": 0, "delete": 0, "skip": 0}
        for _, existing, action, data in plan:
            counts[action] += 1
            if action == "insert": s.add(BlogPost(**data))
            elif action == "update":
                for key, value in data.items(): setattr(existing, key, value)
                if data.get("status") == "published" and not existing.published_at: existing.published_at = datetime.utcnow()
                if data.get("status") == "draft": existing.published_at = None
            elif action == "delete": await s.delete(existing)
        await s.flush(); await _audit(s, user, operation, operation, None, counts); await s.commit()
        return {"ok": True, "operation": operation, **counts}
    except HTTPException:
        await s.rollback(); raise
    except Exception as exc:
        await s.rollback(); raise HTTPException(409, f"Import rolled back: {exc}") from exc
