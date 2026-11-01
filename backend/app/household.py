"""
Module 2 logic: household recognition, OTP challenge, trust-score decay/growth.

Trust score model (kept deliberately simple so it's explainable live):
- New device starts at 50 and is NOT trusted, so its first login triggers an OTP.
- Passing the OTP adds +30 (50 -> 80), which crosses the trust threshold: the device is now remembered
  and later logins from the household IP range skip the OTP.
- Clean login from a device already in the account's known IP range: +5
  (capped at 100), and after reaching 80 the device is marked `is_trusted`
  and stops triggering OTP.
- Login from a brand-new fingerprint and/or an IP far outside the account's
  known range: device starts at 50 but the LOGIN is challenged with OTP
  regardless, since a 50-start device is "unknown" until proven otherwise.
- A device that keeps appearing from wildly different IPs (classic
  credential-sharing pattern) has its trust score reduced by 10 per
  anomalous login, which is the actual anti-sharing mechanism: shared
  credentials generate exactly this pattern.
"""
import random
import string
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app import models

TRUST_START = 50.0
TRUST_GROWTH = 5.0
TRUST_PENALTY = 10.0
TRUST_THRESHOLD = 80.0
TRUST_OTP_BONUS = 30.0     # proving you own the account (OTP) is the strongest trust signal there is
OTP_TTL_MINUTES = 5


def _ip_prefix(ip: str) -> str:
    # /24-style household grouping for demo purposes
    parts = ip.split(".")
    return ".".join(parts[:3]) if len(parts) == 4 else ip


def evaluate_login(db: Session, account: models.Account, ip_address: str, fingerprint: str):
    device = (
        db.query(models.Device)
        .filter(models.Device.account_id == account.id, models.Device.fingerprint == fingerprint)
        .first()
    )

    known_household_ips = {
        _ip_prefix(d.last_seen_ip) for d in account.devices if d.last_seen_ip
    }
    ip_in_household = _ip_prefix(ip_address) in known_household_ips if known_household_ips else True

    if device is None:
        device = models.Device(
            account_id=account.id,
            fingerprint=fingerprint,
            label=f"Device {fingerprint[:6]}",
            trust_score=TRUST_START,
            first_seen_ip=ip_address,
            last_seen_ip=ip_address,
        )
        db.add(device)
        db.flush()
        is_known_device = False
    else:
        is_known_device = device.is_trusted and ip_in_household

    if is_known_device:
        device.trust_score = min(100.0, device.trust_score + TRUST_GROWTH)
    else:
        if device.trust_score is not None and not ip_in_household:
            device.trust_score = max(0.0, device.trust_score - TRUST_PENALTY)

    # trust follows the score in BOTH directions: earned at 80+, lost when it decays below
    device.is_trusted = device.trust_score >= TRUST_THRESHOLD

    device.last_seen_ip = ip_address
    device.last_seen_at = datetime.utcnow()

    return device, is_known_device


def generate_otp(db: Session, login_event: models.LoginEvent) -> models.OTPChallenge:
    code = "".join(random.choices(string.digits, k=6))
    challenge = models.OTPChallenge(
        login_event_id=login_event.id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
    )
    db.add(challenge)
    db.flush()
    return challenge


def verify_otp(db: Session, otp_id: str, code: str) -> bool:
    challenge = db.query(models.OTPChallenge).filter(models.OTPChallenge.id == otp_id).first()
    if not challenge:
        return False
    if challenge.verified:
        return False
    if datetime.utcnow() > challenge.expires_at:
        return False
    if challenge.code != code:
        return False
    challenge.verified = True
    login_event = db.query(models.LoginEvent).filter(
        models.LoginEvent.id == challenge.login_event_id
    ).first()
    if login_event:
        login_event.status = "otp_verified"
        device = db.query(models.Device).filter(models.Device.id == login_event.device_id).first()
        if device:
            device.trust_score = min(100.0, (device.trust_score or 0.0) + TRUST_OTP_BONUS)
            device.is_trusted = device.trust_score >= TRUST_THRESHOLD
    return True
