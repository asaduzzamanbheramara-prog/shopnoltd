"""Guarded data control-plane for BlogPost entities.

Blog content is safe for controlled generic mutation, unlike wallets, ledgers,
identity, audit history, and other security-sensitive stores. Every operation
is tenant-scoped, validated, transactional, and auditable.
"""
import csv
import io
import json
import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.blog import can_manage_blog, current_user
from app.core.db import Base, SessionLocal
from app.models.models import BlogPost

router = APIRouter()
MAX_ROWS = 5000
MAX_BYTES = 10 * 1024 * 1024


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


def _parse_csv(raw: bytes):
    text = raw.decode("utf-8-sig")
    return list(csv.DictReader(io.StringIO(text)))


def _parse_upload(filename: str, raw: bytes):
    lower = filename.lower()
    if lower.endswith(".json"):
        parsed = json.loads(raw.decode("utf-8-sig"))
        return parsed if isinstance(parsed, list) else parsed.get("rows", parsed.get("data", []))
    if lower.endswith(".csv"):
        return _parse_csv(raw)
    if lower.endswith(".xlsx"):
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise HTTPException(503, "XLSX support is not installed") from exc
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        ws = wb.active
        values = list(ws.values)
        if not values:
            return []
        headers = [str(x) if x is not None else "" for x in values[0]]
        return [dict(zip(headers, row)) for row in values[1:]]
    raise HTTPException(415, "Supported import formats: CSV, JSON, XLSX")


async def _match(s: AsyncSession, item: dict, user: dict):
    scope = _scope(user)
    clauses = []
    if item.get("id"):
        clauses.append(BlogPost.id == str(item["id"]))
    if item.get("slug"):
        clauses.append(BlogPost.slug == str(item["slug"]))
    if not clauses:
        return None
    query = select(BlogPost).where(or_(*clauses))
    if scope is not None:
        query = query.where(scope)
    return (await s.execute(query)).scalar_one_or_none()


def _prepare_insert(item: dict, user: dict):
    data = _clean(item)
    now = datetime.utcnow()
    data["id"] = str(item.get("id") or uuid.uuid4())
    data["tenant_id"] = user.get("tenant_id", "default")
    data["author_id"] = user.get("sub", "unknown")
    if data.get("status") == "published":
        data["published_at"] = now
    else:
        data["published_at"] = None
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
                raise HTTPException(409, f"Row already exists for id/slug {raw.get('id') or raw.get('slug')}")
            action = "insert"
        elif operation in {"update", "merge"}:
            if not existing:
                raise HTTPException(404, f"No matching row for id/slug {raw.get('id') or raw.get('slug')}")
            action = "update"
        elif operation == "upsert":
            action = "update" if existing else "insert"
        elif operation == "delete":
            if not existing:
                action = "skip"
            else:
                action = "delete"
        else:
            raise HTTPException(400, f"Unsupported operation: {operation}")
        if action == "insert":
            data = _prepare_insert(raw, user)
        elif action == "update":
            data = _clean(raw, partial=True)
            if operation == "update" and not data:
                raise HTTPException(400, "Update row contains no editable fields")
        else:
            data = {}
        plan.append((raw, existing, action, data))
    return plan


async def _read_rows(user, s):
    query = select(BlogPost).order_by(BlogPost.created_at.desc())
    scope = _scope(user)
    if scope is not None:
        query = query.where(scope)
    return [_row(x) for x in (await s.execute(query.limit(MAX_ROWS))).scalars().all()]


@router.get("/schema")
async def schema(user=Depends(current_user)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    return {
        "entity": "blog_posts",
        "operations": ["add", "update", "upsert", "merge", "delete", "replace_rows", "create_table"],
        "schema_replacement": False,
        "match_keys": ["id", "slug"],
        "fields": [c.name for c in BlogPost.__table__.columns],
        "tenant_scoped": True,
        "transactional": True,
    }


@router.get("/analysis")
async def analysis(user=Depends(current_user), s: AsyncSession = Depends(SessionLocal)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    scope = _scope(user)
    q = select(BlogPost)
    if scope is not None:
        q = q.where(scope)
    posts = (await s.execute(q)).scalars().all()
    status = {"draft": 0, "published": 0}
    for p in posts:
        status[p.status] = status.get(p.status, 0) + 1
    return {
        "rows": len(posts), "columns": len(BlogPost.__table__.columns),
        "status_distribution": status,
        "published_with_content": sum(1 for p in posts if p.status == "published" and p.content),
        "avg_title_length": round(sum(len(p.title) for p in posts) / len(posts), 2) if posts else 0,
        "visualization": {"recommended": "2d+3d", "dimensions": ["status", "created_at", "published_at"]},
    }


@router.get("/export")
async def export_data(format: str = Query("json", pattern="^(json|csv|xlsx|pdf)$"), user=Depends(current_user), s: AsyncSession = Depends(SessionLocal)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    rows = await _read_rows(user, s)
    if format == "json":
        body = json.dumps({"entity": "blog_posts", "version": 1, "rows": rows}, indent=2).encode()
        return StreamingResponse(io.BytesIO(body), media_type="application/json", headers={"Content-Disposition": "attachment; filename=blog_posts.json"})
    if format == "csv":
        out = io.StringIO(); writer = csv.DictWriter(out, fieldnames=[c.name for c in BlogPost.__table__.columns]); writer.writeheader(); writer.writerows(rows)
        return StreamingResponse(io.BytesIO(out.getvalue().encode()), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=blog_posts.csv"})
    if format == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError as exc:
            raise HTTPException(503, "XLSX support is not installed") from exc
        wb = Workbook(); ws = wb.active; ws.title = "blog_posts"; fields = [c.name for c in BlogPost.__table__.columns]; ws.append(fields)
        for row in rows: ws.append([row.get(k) for k in fields])
        out = io.BytesIO(); wb.save(out); out.seek(0)
        return StreamingResponse(out, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=blog_posts.xlsx"})
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    except ImportError as exc:
        raise HTTPException(503, "PDF reporting is not installed") from exc
    out = io.BytesIO(); doc = SimpleDocTemplate(out, pagesize=A4); story = [Paragraph("Shopnoltd Blog Data Report", None), Spacer(1, 12)]
    story.append(Paragraph(f"Rows: {len(rows)}", None)); story.append(Paragraph(f"Generated: {datetime.utcnow().isoformat()}Z", None)); doc.build(story); out.seek(0)
    return StreamingResponse(out, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=blog_posts.pdf"})


@router.post("/import/preview")
async def preview_import(operation: str = Query("add"), file: UploadFile = File(...), user=Depends(current_user), s: AsyncSession = Depends(SessionLocal)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    if operation in {"create_table", "replace_schema"}:
        raise HTTPException(403, "Schema creation/replacement is not available for service-owned BlogPost schema")
    raw = await file.read()
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, f"Maximum upload size is {MAX_BYTES} bytes")
    items = _parse_upload(file.filename or "import", raw)
    if operation == "replace_rows":
        if len(items) > MAX_ROWS: raise HTTPException(413, f"Maximum import size is {MAX_ROWS} rows")
        return {"operation": operation, "rows": len(items), "will_delete_existing": True, "preview": items[:20]}
    plan = await _plan(items, operation, user, s)
    return {"operation": operation, "rows": len(items), "counts": {"insert": sum(x[2] == "insert" for x in plan), "update": sum(x[2] == "update" for x in plan), "delete": sum(x[2] == "delete" for x in plan), "skip": sum(x[2] == "skip" for x in plan)}, "preview": [{"action": x[2], "row": x[0]} for x in plan[:20]]}


@router.post("/import")
async def commit_import(operation: str = Query("add"), confirm: bool = Query(False), file: UploadFile = File(...), user=Depends(current_user), s: AsyncSession = Depends(SessionLocal)):
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
            scope = _scope(user)
            stmt = delete(BlogPost)
            if scope is not None: stmt = stmt.where(scope)
            result = await s.execute(stmt)
            deleted = result.rowcount or 0
            for item in items:
                s.add(BlogPost(**_prepare_insert(item, user)))
            await _audit(s, user, "replace_rows", operation, {"deleted": deleted}, {"inserted": len(items)})
            await s.commit()
            return {"ok": True, "operation": operation, "deleted": deleted, "inserted": len(items)}
        plan = await _plan(items, operation, user, s)
        counts = {"insert": 0, "update": 0, "delete": 0, "skip": 0}
        for raw_item, existing, action, data in plan:
            counts[action] += 1
            if action == "insert":
                s.add(BlogPost(**data))
            elif action == "update":
                for key, value in data.items(): setattr(existing, key, value)
                if data.get("status") == "published" and not existing.published_at:
                    existing.published_at = datetime.utcnow()
                if data.get("status") == "draft": existing.published_at = None
            elif action == "delete":
                await s.delete(existing)
        await s.flush()
        await _audit(s, user, operation, operation, None, counts)
        await s.commit()
        return {"ok": True, "operation": operation, **counts}
    except HTTPException:
        await s.rollback(); raise
    except Exception as exc:
        await s.rollback()
        raise HTTPException(409, f"Import rolled back: {exc}") from exc
