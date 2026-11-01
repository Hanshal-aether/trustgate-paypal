"""
SQLAlchemy models.

ID strategy (Module 3 decision, documented in README):
- UUIDv4 for security-sensitive IDs (sessions, OTP challenges) -> non-guessable.
- UUIDv7-style (time-ordered) for event/log rows (signups, logins) -> keeps
  indexes efficient as the table grows, while staying globally unique.
We implement a lightweight uuid7() helper below instead of adding a new
dependency, since Python's stdlib uuid module doesn't ship v7 yet.
"""
import os
import time
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Float, Integer, DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def uuid4_str() -> str:
    return str(uuid.uuid4())


def uuid7_str() -> str:
    """Minimal UUIDv7: 48-bit ms timestamp + random bits. Time-ordered,
    so rows inserted close together stay close together in a B-tree index."""
    unix_ts_ms = int(time.time() * 1000)
    ts_bytes = unix_ts_ms.to_bytes(6, byteorder="big")
    rand_bytes = os.urandom(10)
    # Set version (7) and variant bits per RFC draft
    b = bytearray(ts_bytes + rand_bytes)
    b[6] = (b[6] & 0x0F) | 0x70
    b[8] = (b[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(b)))


class Account(Base):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=uuid4_str)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    devices = relationship("Device", back_populates="account")
    signup_events = relationship("SignupEvent", back_populates="account")
    login_events = relationship("LoginEvent", back_populates="account")


class SignupEvent(Base):
    __tablename__ = "signup_events"
    id = Column(String, primary_key=True, default=uuid7_str)  # event log -> uuid7
    account_id = Column(String, ForeignKey("accounts.id"), nullable=True)
    email = Column(String, index=True)
    ip_address = Column(String, index=True)
    ip_type = Column(String)          # "residential" | "hosting" | "unknown"
    fingerprint = Column(String, index=True)
    risk_score = Column(Float)
    decision = Column(String)          # allow | flag | block
    reasons = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    account = relationship("Account", back_populates="signup_events")


class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True, default=uuid4_str)  # security-sensitive -> uuid4
    account_id = Column(String, ForeignKey("accounts.id"))
    fingerprint = Column(String, index=True)
    label = Column(String, default="Unknown device")
    trust_score = Column(Float, default=50.0)
    first_seen_ip = Column(String)
    last_seen_ip = Column(String)
    is_trusted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)

    account = relationship("Account", back_populates="devices")


class LoginEvent(Base):
    __tablename__ = "login_events"
    id = Column(String, primary_key=True, default=uuid7_str)  # event log -> uuid7
    account_id = Column(String, ForeignKey("accounts.id"))
    device_id = Column(String, ForeignKey("devices.id"), nullable=True)
    ip_address = Column(String)
    fingerprint = Column(String)
    is_known_device = Column(Boolean)
    otp_required = Column(Boolean, default=False)
    otp_id = Column(String, nullable=True)  # security-sensitive -> uuid4
    status = Column(String, default="success")  # success | otp_pending | otp_verified | blocked
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    account = relationship("Account", back_populates="login_events")


class OTPChallenge(Base):
    __tablename__ = "otp_challenges"
    id = Column(String, primary_key=True, default=uuid4_str)  # security-sensitive -> uuid4
    login_event_id = Column(String, ForeignKey("login_events.id"))
    code = Column(String)
    expires_at = Column(DateTime)
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
