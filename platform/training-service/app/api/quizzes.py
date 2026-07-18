from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Quiz, QuizAttempt
from app.schemas.schemas import QuizIn, QuizSubmit

router = APIRouter()
bearer = HTTPBearer()


async def db():
    async with SessionLocal() as s:
        yield s


async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)


@router.post("", status_code=201)
async def create(body: QuizIn, user=Depends(current_user), s: AsyncSession = Depends(db)):
    q = Quiz(**body.model_dump())
    s.add(q)
    await s.commit()
    return {"id": q.id}


@router.get("/{quiz_id}")
async def get(quiz_id: str, s: AsyncSession = Depends(db)):
    q = (await s.execute(select(Quiz).where(Quiz.id == quiz_id))).scalar_one_or_none()
    if not q:
        raise HTTPException(404, "not found")
    return {
        "id": q.id,
        "title": q.title,
        "questions": [{"q": x["q"], "choices": x["choices"]} for x in (q.questions or [])],
        "passing_score": q.passing_score,
    }


@router.post("/submit", status_code=201)
async def submit(body: QuizSubmit, user=Depends(current_user), s: AsyncSession = Depends(db)):
    q = (await s.execute(select(Quiz).where(Quiz.id == body.quiz_id))).scalar_one_or_none()
    if not q:
        raise HTTPException(404, "not found")
    correct = 0
    total = len(q.questions or [])
    for i, question in enumerate(q.questions or []):
        if body.answers.get(str(i)) == question.get("correct"):
            correct += 1
    score = (correct / total * 100) if total else 0
    passed = 1 if score >= q.passing_score else 0
    a = QuizAttempt(
        quiz_id=q.id, user_id=user["sub"], score=score, passed=passed, answers=body.answers
    )
    s.add(a)
    await s.commit()
    return {"score": score, "passed": bool(passed), "correct": correct, "total": total}
