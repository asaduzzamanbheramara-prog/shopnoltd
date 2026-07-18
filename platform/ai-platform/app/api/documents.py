from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Chunk, Document
from app.schemas.schemas import DocIn

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


def chunk_text(t: str, size: int = 500) -> list:
    return [t[i : i + size] for i in range(0, len(t), size)]


@router.post("", status_code=201)
async def create(body: DocIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    d = Document(
        tenant_id=user.get("tenant_id", "default"),
        user_id=user["sub"],
        title=body.title,
        source_uri=body.source_uri,
        text=body.text,
        chunk_count=0,
    )
    s.add(d)
    await s.commit()
    await s.refresh(d)
    if body.text:
        chunks = chunk_text(body.text)
        for i, c in enumerate(chunks):
            s.add(Chunk(document_id=d.id, idx=i, text=c, embedding="[]"))
        d.chunk_count = len(chunks)
        await s.commit()
    return {"id": d.id, "title": d.title, "chunks": d.chunk_count}


@router.get("")
async def list_docs(user=Depends(current_user), s: AsyncSession = Depends(db)):
    res = await s.execute(
        select(Document)
        .where(Document.user_id == user["sub"])
        .order_by(Document.created_at.desc())
        .limit(100)
    )
    return [
        {
            "id": d.id,
            "title": d.title,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at.isoformat(),
        }
        for d in res.scalars().all()
    ]


@router.post("/{doc_id}/search")
async def search(
    doc_id: str, query: str, user=Depends(current_user), s: AsyncSession = Depends(db)
):
    res = await s.execute(select(Chunk).where(Chunk.document_id == doc_id))
    chunks = res.scalars().all()
    scored = sorted(
        [
            (c, query.lower().count(c.text.lower()[:50].split()[0] if c.text else ""))
            for c in chunks
        ],
        key=lambda x: x[1],
        reverse=True,
    )
    return [{"idx": c.idx, "text": c.text[:300], "score": score} for c, score in scored[:5]]
