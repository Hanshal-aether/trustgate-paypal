from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas, household

router = APIRouter(prefix="/api", tags=["login"])


@router.post("/login-check", response_model=schemas.LoginCheckResponse)
def login_check(payload: schemas.LoginCheckRequest, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.email == payload.email).first()
    if not account:
        raise HTTPException(status_code=404, detail="No account with this email. Sign up first.")

    device, is_known_device = household.evaluate_login(
        db, account, payload.ip_address, payload.fingerprint
    )

    login_event = models.LoginEvent(
        account_id=account.id,
        device_id=device.id,
        ip_address=payload.ip_address,
        fingerprint=payload.fingerprint,
        is_known_device=is_known_device,
        otp_required=not is_known_device,
        status="success" if is_known_device else "otp_pending",
    )
    db.add(login_event)
    db.flush()

    if is_known_device:
        db.commit()
        return schemas.LoginCheckResponse(
            status="success",
            is_known_device=True,
            message="Recognized device and household IP. Logged in.",
        )

    challenge = household.generate_otp(db, login_event)
    login_event.otp_id = challenge.id
    db.commit()

    # Demo-only: real product emails/push-notifies the code to the owner's
    # trusted device instead of returning it in the API response.
    return schemas.LoginCheckResponse(
        status="otp_pending",
        is_known_device=False,
        otp_id=challenge.id,
        message=f"New device/location detected. OTP sent to trusted device. (DEMO CODE: {challenge.code})",
    )


@router.post("/otp/verify")
def otp_verify(payload: schemas.OTPVerifyRequest, db: Session = Depends(get_db)):
    ok = household.verify_otp(db, payload.otp_id, payload.code)
    db.commit()
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code.")
    return {"status": "verified"}
