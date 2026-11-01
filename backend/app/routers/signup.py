from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, hybrid

router = APIRouter(prefix="/api", tags=["signup"])


@router.post("/signup-check", response_model=schemas.SignupCheckResponse)
def signup_check(payload: schemas.SignupCheckRequest, db: Session = Depends(get_db)):
    result = hybrid.score_signup_hybrid(payload.email, payload.ip_address, payload.fingerprint, payload.user_agent)

    account = db.query(models.Account).filter(models.Account.email == payload.email).first()
    if account is None and result["decision"] != "block":
        account = models.Account(email=payload.email)
        db.add(account)
        db.flush()

    event = models.SignupEvent(
        account_id=account.id if account else None,
        email=payload.email,
        ip_address=payload.ip_address,
        ip_type=result["ip_type"],
        fingerprint=payload.fingerprint,
        risk_score=result["risk_score"],
        decision=result["decision"],
        reasons=result["reasons"],
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return schemas.SignupCheckResponse(
        risk_score=result["risk_score"],
        decision=result["decision"],
        reasons=result["reasons"],
        event_id=event.id,
        rule_score=result["rule_score"],
        ml_score=result["ml_score"],
        ml_enabled=result["ml_enabled"],
    )
