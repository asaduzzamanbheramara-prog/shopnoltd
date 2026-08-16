from app.models.db import Proxy, get_db
from app.models.schemas import ProxyCreate, ProxyOut
from app.services.crypto import encrypt_secret
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("", response_model=list[ProxyOut])
def list_proxies(db: Session = Depends(get_db)):
    return db.query(Proxy).all()


@router.post("", response_model=ProxyOut)
def create_proxy(payload: ProxyCreate, db: Session = Depends(get_db)):
    proxy = Proxy(
        label=payload.label,
        server=payload.server,
        username=payload.username,
        password_encrypted=encrypt_secret(payload.password) if payload.password else None,
        country=payload.country,
    )
    db.add(proxy)
    db.commit()
    db.refresh(proxy)
    return proxy


@router.delete("/{proxy_id}")
def delete_proxy(proxy_id: str, db: Session = Depends(get_db)):
    proxy = db.query(Proxy).filter(Proxy.id == proxy_id).first()
    if proxy:
        db.delete(proxy)
        db.commit()
    return {"deleted": bool(proxy)}
