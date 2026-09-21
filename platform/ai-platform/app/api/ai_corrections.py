from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.core.security import current_user
from app.db.session import get_db
from app.services.model_router import run_inference

router = APIRouter(prefix="/api/v1/ai/corrections", tags=["ai-corrections"])


class CorrectionRequest(BaseModel):
    text: str
    instruction: str = "Correct errors while preserving meaning."
    model: str | None = None


@router.post("/propose")
async def propose(body: CorrectionRequest, user=Depends(current_user), db=Depends(get_db)):
    prompt = (
        "You are Shopnoltd's correction assistant. Return ONLY the corrected text, "
        "then a short 'CHANGES:' section describing what was corrected. Never invent facts.\n\n"
        f"Instruction: {body.instruction}\n\nTEXT:\n{body.text}"
    )
    result = await run_inference(db=db, prompt=prompt, model_name=body.model, attachments=[])
    return {"mode": "propose", "corrected_text": result.text, "tokens": result.tokens_used}


@router.post("/fix")
async def fix(body: CorrectionRequest, user=Depends(current_user), db=Depends(get_db)):
    prompt = (
        "Act as a careful code/text fixer. Return a corrected version and a concise "
        "CHANGES section. Do not claim to have executed or verified anything.\n\n"
        f"Instruction: {body.instruction}\n\nINPUT:\n{body.text}"
    )
    result = await run_inference(db=db, prompt=prompt, model_name=body.model, attachments=[])
    return {"mode": "fix", "proposal": result.text, "requires_approval": True, "tokens": result.tokens_used}
