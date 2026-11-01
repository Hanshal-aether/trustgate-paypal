from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/signups", response_model=list[schemas.SignupEventOut])
def recent_signups(limit: int = 50, db: Session = Depends(get_db)):
    events = (
        db.query(models.SignupEvent)
        .order_by(models.SignupEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    return events


@router.get("/devices", response_model=list[schemas.DeviceOut])
def all_devices(limit: int = 50, db: Session = Depends(get_db)):
    devices = (
        db.query(models.Device)
        .order_by(models.Device.last_seen_at.desc())
        .limit(limit)
        .all()
    )
    return devices


@router.get("/stats", response_model=schemas.DashboardStats)
def stats(db: Session = Depends(get_db)):
    total = db.query(func.count(models.SignupEvent.id)).scalar() or 0
    allowed = db.query(func.count(models.SignupEvent.id)).filter(
        models.SignupEvent.decision == "allow"
    ).scalar() or 0
    flagged = db.query(func.count(models.SignupEvent.id)).filter(
        models.SignupEvent.decision == "flag"
    ).scalar() or 0
    blocked = db.query(func.count(models.SignupEvent.id)).filter(
        models.SignupEvent.decision == "block"
    ).scalar() or 0
    total_devices = db.query(func.count(models.Device.id)).scalar() or 0
    trusted_devices = db.query(func.count(models.Device.id)).filter(
        models.Device.is_trusted == True  # noqa: E712
    ).scalar() or 0

    return schemas.DashboardStats(
        total_signups=total,
        allowed=allowed,
        flagged=flagged,
        blocked=blocked,
        total_devices=total_devices,
        trusted_devices=trusted_devices,
    )


@router.get("/accounts", response_model=list[schemas.AccountOut])
def accounts(limit: int = 50, db: Session = Depends(get_db)):
    """Accounts with their devices, for the Households screen."""
    return (
        db.query(models.Account)
        .order_by(models.Account.created_at.desc())
        .limit(limit)
        .all()
    )
