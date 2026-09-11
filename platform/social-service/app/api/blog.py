from datetime import datetime, timezone
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import BlogPost

router = APIRouter()
bearer = HTTPBearer(auto_error=False)


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if creds is None:
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})
    return await verify_token(creds.credentials)


def is_staff(user: dict) -> bool:
    roles = set(user.get("roles", []))
    return bool(roles.intersection({"admin", "platform_admin"}))


def can_manage_blog(user: dict) -> bool:
    """Return whether the caller may access tenant/global blog administration."""
    roles = set(user.get("roles", []))
    return bool(roles.intersection({"admin", "platform_admin", "tenant_owner"}))


# Keep blog administration authorization shared by normal and data-control-plane routes.

def can_manage_post(user: dict, post: BlogPost) -> bool:
    if is_staff(user):
        return True
    tenant_id = user.get("tenant_id", "default")
    return post.tenant_id == tenant_id and post.author_id == user.get("sub")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "post"


class BlogPostIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    slug: str | None = Field(default=None, max_length=320)
    excerpt: str | None = None
    content: str = Field(min_length=1)
    cover_image: str | None = None
    status: str = Field(default="draft", pattern="^(draft|published)$")


class BlogPostOut(BaseModel):
    id: str
    title: str
    slug: str
    excerpt: str | None
    content: str
    cover_image: str | None
    status: str
    published_at: str | None
    created_at: str
    updated_at: str


def out(p: BlogPost) -> BlogPostOut:
    return BlogPostOut(
        id=p.id,
        title=p.title,
        slug=p.slug,
        excerpt=p.excerpt,
        content=p.content,
        cover_image=p.cover_image,
        status=p.status,
        published_at=p.published_at.isoformat() if p.published_at else None,
        created_at=p.created_at.isoformat(),
        updated_at=p.updated_at.isoformat(),
    )


@router.get("", response_model=list[BlogPostOut])
async def public_blog(
    limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0), s: AsyncSession = Depends(db)
):
    res = await s.execute(
        select(BlogPost)
        .where(BlogPost.status == "published")
        .order_by(desc(BlogPost.published_at))
        .limit(limit)
        .offset(offset)
    )
    return [out(p) for p in res.scalars().all()]


@router.get("/mine", response_model=list[BlogPostOut])
async def my_blog(user=Depends(current_user), s: AsyncSession = Depends(db)):
    query = (
        select(BlogPost)
        .where(
            BlogPost.tenant_id == user.get("tenant_id", "default"),
            BlogPost.author_id == user.get("sub"),
        )
        .order_by(desc(BlogPost.updated_at))
    )
    res = await s.execute(query)
    return [out(p) for p in res.scalars().all()]


@router.get("/admin", response_model=list[BlogPostOut])
async def admin_blog(user=Depends(current_user), s: AsyncSession = Depends(db)):
    if not can_manage_blog(user):
        raise HTTPException(403, "Blog management privileges required")
    roles = set(user.get("roles", []))
    query = select(BlogPost).order_by(desc(BlogPost.updated_at))
    if not roles.intersection({"admin", "platform_admin"}):
        query = query.where(BlogPost.tenant_id == user.get("tenant_id", "default"))
    res = await s.execute(query)
    return [out(p) for p in res.scalars().all()]


@router.get("/{slug}", response_model=BlogPostOut)
async def get_blog_post(slug: str, s: AsyncSession = Depends(db)):
    res = await s.execute(select(BlogPost).where(BlogPost.slug == slug, BlogPost.status == "published"))
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(404, "blog post not found")
    return out(p)


@router.post("", response_model=BlogPostOut, status_code=201)
async def create_blog_post(body: BlogPostIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    slug = slugify(body.slug or body.title)
    if (await s.execute(select(BlogPost).where(BlogPost.slug == slug))).scalar_one_or_none():
        raise HTTPException(409, "slug already exists")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    p = BlogPost(
        tenant_id=user.get("tenant_id", "default"),
        author_id=user["sub"],
        title=body.title,
        slug=slug,
        excerpt=body.excerpt,
        content=body.content,
        cover_image=body.cover_image,
        status=body.status,
        published_at=now if body.status == "published" else None,
    )
    s.add(p)
    await s.commit()
    await s.refresh(p)
    return out(p)


@router.put("/{post_id}", response_model=BlogPostOut)
async def update_blog_post(post_id: str, body: BlogPostIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(BlogPost).where(BlogPost.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "blog post not found")
    if not can_manage_post(user, p):
        raise HTTPException(403, "You cannot manage this blog post")
    slug = slugify(body.slug or body.title)
    conflict = (await s.execute(select(BlogPost).where(BlogPost.slug == slug, BlogPost.id != post_id))).scalar_one_or_none()
    if conflict:
        raise HTTPException(409, "slug already exists")
    was_published = p.status == "published"
    p.title = body.title
    p.slug = slug
    p.excerpt = body.excerpt
    p.content = body.content
    p.cover_image = body.cover_image
    p.status = body.status
    if body.status == "published" and not was_published:
        p.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
    elif body.status == "draft":
        p.published_at = None
    await s.commit()
    await s.refresh(p)
    return out(p)


@router.delete("/{post_id}")
async def delete_blog_post(post_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    p = (await s.execute(select(BlogPost).where(BlogPost.id == post_id))).scalar_one_or_none()
    if not p:
        raise HTTPException(404, "blog post not found")
    if not can_manage_post(user, p):
        raise HTTPException(403, "You cannot manage this blog post")
    await s.delete(p)
    await s.commit()
    return {"ok": True}
