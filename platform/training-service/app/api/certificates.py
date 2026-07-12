import io, secrets
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db import SessionLocal
from app.core.security import verify_token
from app.models.models import Certificate, Enrollment, Course
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
router = APIRouter(); bearer = HTTPBearer()
async def db():
    async with SessionLocal() as s: yield s
async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer)):
    return await verify_token(creds.credentials)
@router.post("/{enrollment_id}", status_code=201)
async def issue(enrollment_id: str, user=Depends(current_user), s: AsyncSession = Depends(db)):
    e = (await s.execute(select(Enrollment).where(Enrollment.id == enrollment_id, Enrollment.user_id == user["sub"]))).scalar_one_or_none()
    if not e: raise HTTPException(404, "not found")
    if e.status != "completed": raise HTTPException(400, "course not completed")
    existing = (await s.execute(select(Certificate).where(Certificate.enrollment_id == enrollment_id))).scalar_one_or_none()
    if existing: return {"id": existing.id, "serial": existing.serial}
    serial = f"SHOPNO-CERT-{secrets.token_hex(6).upper()}"
    c = Certificate(enrollment_id=enrollment_id, user_id=user["sub"], course_id=e.course_id, serial=serial)
    s.add(c); await s.commit()
    return {"id": c.id, "serial": serial, "issued_at": c.issued_at.isoformat()}
@router.get("/{serial}/pdf")
async def pdf(serial: str, s: AsyncSession = Depends(db)):
    cert = (await s.execute(select(Certificate).where(Certificate.serial == serial))).scalar_one_or_none()
    if not cert: raise HTTPException(404, "not found")
    course = (await s.execute(select(Course).where(Course.id == cert.course_id))).scalar_one()
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=letter)
    p.setFont("Helvetica-Bold", 28); p.drawCentredString(4.25*inch, 9*inch, "Shopnoltd")
    p.setFont("Helvetica-Bold", 20); p.drawCentredString(4.25*inch, 8*inch, "Certificate of Completion")
    p.setFont("Helvetica", 14); p.drawCentredString(4.25*inch, 7*inch, f"Awarded to user {cert.user_id}")
    p.drawCentredString(4.25*inch, 6.5*inch, f"for completing the course")
    p.setFont("Helvetica-Bold", 16); p.drawCentredString(4.25*inch, 6*inch, course.title)
    p.setFont("Helvetica", 10); p.drawCentredString(4.25*inch, 3*inch, f"Serial: {cert.serial}")
    p.drawCentredString(4.25*inch, 2.7*inch, f"Issued: {cert.issued_at.strftime('%Y-%m-%d')}")
    p.showPage(); p.save()
    return Response(buf.getvalue(), media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={serial}.pdf"})
