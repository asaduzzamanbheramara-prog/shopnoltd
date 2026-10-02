from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
import dns.asyncresolver

from .db import get_db
from .models import AdZone, Advertiser, Campaign, Creative, Publisher, PublisherSite
from .schemas import CampaignCreate, CreativeCreate, OwnerCreate, SiteCreate, ZoneCreate
from .security import current_user, require_admin

router = APIRouter(prefix="/v1/ads", tags=["advertising"])


def subject(user: dict) -> str:
    return str(user["sub"])


async def owned_advertiser(db: AsyncSession, user: dict) -> Advertiser:
    row = await db.scalar(select(Advertiser).where(Advertiser.owner_user_id == subject(user)))
    if not row:
        raise HTTPException(404, "Advertiser account not found")
    return row


async def owned_publisher(db: AsyncSession, user: dict) -> Publisher:
    row = await db.scalar(select(Publisher).where(Publisher.owner_user_id == subject(user)))
    if not row:
        raise HTTPException(404, "Publisher account not found")
    return row


@router.post("/advertisers", status_code=201)
async def register_advertiser(body: OwnerCreate, user=Depends(current_user), db=Depends(get_db)):
    existing = await db.scalar(select(Advertiser).where(Advertiser.owner_user_id == subject(user)))
    if existing:
        raise HTTPException(409, "Advertiser account already exists")
    row = Advertiser(owner_user_id=subject(user), legal_name=body.display_name)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Advertiser account already exists") from None
    await db.refresh(row)
    return {"id": str(row.id), "status": row.status, "legal_name": row.legal_name}


@router.get("/advertisers/me")
async def get_advertiser(user=Depends(current_user), db=Depends(get_db)):
    row = await owned_advertiser(db, user)
    return {"id": str(row.id), "status": row.status, "legal_name": row.legal_name}


@router.post("/publishers", status_code=201)
async def register_publisher(body: OwnerCreate, user=Depends(current_user), db=Depends(get_db)):
    existing = await db.scalar(select(Publisher).where(Publisher.owner_user_id == subject(user)))
    if existing:
        raise HTTPException(409, "Publisher account already exists")
    row = Publisher(owner_user_id=subject(user), display_name=body.display_name)
    db.add(row)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "Publisher account already exists") from None
    await db.refresh(row)
    return {"id": str(row.id), "status": row.status, "display_name": row.display_name}


@router.get("/publishers/me")
async def get_publisher(user=Depends(current_user), db=Depends(get_db)):
    row = await owned_publisher(db, user)
    return {"id": str(row.id), "status": row.status, "display_name": row.display_name, "revenue_share_bps": row.revenue_share_bps}


@router.post("/publishers/sites", status_code=201)
async def create_site(body: SiteCreate, user=Depends(current_user), db=Depends(get_db)):
    publisher = await owned_publisher(db, user)
    domain = body.domain.strip().lower().rstrip(".")
    if publisher.status != "approved":
        raise HTTPException(403, "Publisher account must be approved before adding inventory")
    existing = await db.scalar(select(PublisherSite).where(PublisherSite.publisher_id == publisher.id, PublisherSite.domain == domain))
    if existing:
        raise HTTPException(409, "Site already registered")
    import secrets
    row = PublisherSite(
        publisher_id=publisher.id,
        domain=domain,
        verification_method="dns",
        verification_token=secrets.token_urlsafe(32),
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "domain": row.domain, "verification_status": row.verification_status, "verification_token": row.verification_token}


@router.post("/publishers/sites/{site_id}/verify")
async def verify_site(site_id: UUID, user=Depends(current_user), db=Depends(get_db)):
    publisher = await owned_publisher(db, user)
    site = await db.scalar(select(PublisherSite).where(PublisherSite.id == site_id, PublisherSite.publisher_id == publisher.id))
    if not site:
        raise HTTPException(404, "Site not found")
    if publisher.status != "approved":
        raise HTTPException(403, "Publisher account must be approved before verifying inventory")
    record_name = f"_shopnoltd-verify.{site.domain}".rstrip(".")
    resolver = dns.asyncresolver.Resolver()
    resolver.timeout = 3.0
    resolver.lifetime = 5.0
    try:
        answers = await resolver.resolve(record_name, "TXT")
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers, dns.exception.Timeout):
        site.verification_status = "failed"
        await db.commit()
        raise HTTPException(422, f"DNS TXT verification record not found at {record_name}") from None
    token = site.verification_token
    values = {"".join(part.decode("utf-8") if isinstance(part, bytes) else part for part in r.strings) for r in answers}
    if token not in values:
        site.verification_status = "failed"
        await db.commit()
        raise HTTPException(422, "DNS TXT verification token does not match")
    site.verification_method = "dns"
    site.verification_status = "verified"
    await db.commit()
    return {"id": str(site.id), "domain": site.domain, "verification_status": site.verification_status, "record_name": record_name}


@router.post("/publishers/sites/{site_id}/zones", status_code=201)
async def create_zone(site_id: UUID, body: ZoneCreate, user=Depends(current_user), db=Depends(get_db)):
    publisher = await owned_publisher(db, user)
    site = await db.scalar(select(PublisherSite).where(PublisherSite.id == site_id, PublisherSite.publisher_id == publisher.id))
    if not site:
        raise HTTPException(404, "Site not found")
    if site.verification_status != "verified":
        raise HTTPException(403, "Site ownership must be verified before creating ad zones")
    row = AdZone(site_id=site.id, name=body.name.strip(), width=body.width, height=body.height)
    db.add(row)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(409, "Ad zone already exists") from None
    await db.refresh(row)
    return {"id": str(row.id), "name": row.name, "width": row.width, "height": row.height, "status": row.status}


@router.post("/campaigns", status_code=201)
async def create_campaign(body: CampaignCreate, user=Depends(current_user), db=Depends(get_db)):
    advertiser = await owned_advertiser(db, user)
    if advertiser.status != "approved":
        raise HTTPException(403, "Advertiser account must be approved before creating campaigns")
    if body.ends_at <= body.starts_at:
        raise HTTPException(422, "ends_at must be after starts_at")
    row = Campaign(advertiser_id=advertiser.id, **body.model_dump())
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "status": row.status, "budget_minor": row.budget_minor, "currency": row.currency}


@router.get("/campaigns")
async def list_campaigns(user=Depends(current_user), db=Depends(get_db)):
    advertiser = await owned_advertiser(db, user)
    rows = (await db.scalars(select(Campaign).where(Campaign.advertiser_id == advertiser.id).order_by(Campaign.created_at.desc()))).all()
    return [{"id": str(x.id), "name": x.name, "status": x.status, "budget_minor": x.budget_minor, "spent_minor": x.spent_minor, "currency": x.currency} for x in rows]


@router.post("/creatives", status_code=201)
async def create_creative(body: CreativeCreate, user=Depends(current_user), db=Depends(get_db)):
    advertiser = await owned_advertiser(db, user)
    campaign = await db.scalar(select(Campaign).where(Campaign.id == body.campaign_id, Campaign.advertiser_id == advertiser.id))
    if not campaign:
        raise HTTPException(404, "Campaign not found")
    row = Creative(campaign_id=campaign.id, **{**body.model_dump(exclude={"campaign_id"}), "asset_url": str(body.asset_url), "click_url": str(body.click_url)})
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {"id": str(row.id), "status": row.status, "campaign_id": str(row.campaign_id)}


@router.get("/admin/advertisers")
async def admin_advertisers(user=Depends(require_admin), db=Depends(get_db)):
    rows = (await db.scalars(select(Advertiser).order_by(Advertiser.created_at.desc()))).all()
    return [{"id": str(x.id), "owner_user_id": x.owner_user_id, "legal_name": x.legal_name, "status": x.status} for x in rows]


@router.post("/admin/advertisers/{advertiser_id}/approve")
async def approve_advertiser(advertiser_id: UUID, user=Depends(require_admin), db=Depends(get_db)):
    row = await db.get(Advertiser, advertiser_id)
    if not row:
        raise HTTPException(404, "Advertiser not found")
    row.status = "approved"
    await db.commit()
    return {"id": str(row.id), "status": row.status}


@router.get("/admin/publishers")
async def admin_publishers(user=Depends(require_admin), db=Depends(get_db)):
    rows = (await db.scalars(select(Publisher).order_by(Publisher.created_at.desc()))).all()
    return [{"id": str(x.id), "owner_user_id": x.owner_user_id, "display_name": x.display_name, "status": x.status, "revenue_share_bps": x.revenue_share_bps} for x in rows]


@router.post("/admin/publishers/{publisher_id}/approve")
async def approve_publisher(publisher_id: UUID, user=Depends(require_admin), db=Depends(get_db)):
    row = await db.get(Publisher, publisher_id)
    if not row:
        raise HTTPException(404, "Publisher not found")
    row.status = "approved"
    await db.commit()
    return {"id": str(row.id), "status": row.status}
