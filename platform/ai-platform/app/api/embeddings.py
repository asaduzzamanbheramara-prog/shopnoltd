from fastapi import APIRouter, Depends
from app.core.security import verify_token
from app.core.config import settings
from app.schemas.schemas import EmbedIn, EmbedOut
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
_model = None
def load_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(settings.embedding_model)
        except Exception:
            _model = "stub"
    return _model
@router.post("", response_model=EmbedOut)
async def embed(body: EmbedIn, user=Depends(current_user)):
    m = load_model()
    if m == "stub":
        import hashlib
        out = [[int.from_bytes(hashlib.md5(t.encode()).digest()[:4], "big") / 1e9 for _ in range(8)] for t in body.texts]
        return EmbedOut(embeddings=out, model=settings.embedding_model + " (stub)", dim=8)
    vecs = m.encode(body.texts).tolist()
    return EmbedOut(embeddings=vecs, model=settings.embedding_model, dim=len(vecs[0]) if vecs else 0)
