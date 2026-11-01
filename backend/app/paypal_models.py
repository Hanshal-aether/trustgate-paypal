from datetime import datetime

from sqlalchemy import Column, DateTime, Float, JSON, String

from app.database import Base
from app.models import uuid7_str


class AppSetting(Base):
    __tablename__ = "app_settings"
    key = Column(String, primary_key=True)
    value = Column(String)


class TrialSubscription(Base):
    """One free-trial attempt on the demo SaaS, from TrustGate's decision to the PayPal subscription."""
    __tablename__ = "trial_subscriptions"
    id = Column(String, primary_key=True, default=uuid7_str)
    email = Column(String, index=True)
    fingerprint = Column(String)
    ip_address = Column(String)
    risk_score = Column(Float)
    decision = Column(String)                        # allow | flag | block (TrustGate's call)
    reasons = Column(JSON)
    status = Column(String, default="blocked")       # blocked | challenged | awaiting_paypal | active | cancelled_abuse | cancelled
    challenge_code = Column(String, nullable=True)
    challenge_expires_at = Column(DateTime, nullable=True)
    paypal_subscription_id = Column(String, index=True, nullable=True)
    paypal_payer_id = Column(String, index=True, nullable=True)
    paypal_payer_email = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
