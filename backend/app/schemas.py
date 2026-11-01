from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel


class SignupCheckRequest(BaseModel):
    email: str
    ip_address: str
    fingerprint: str
    user_agent: Optional[str] = None      # optional; lets the ML model use device type


class SignupCheckResponse(BaseModel):
    risk_score: float
    decision: str
    reasons: List[str]
    event_id: str
    rule_score: Optional[float] = None
    ml_score: Optional[float] = None
    ml_enabled: bool = False


class LoginCheckRequest(BaseModel):
    email: str
    ip_address: str
    fingerprint: str


class LoginCheckResponse(BaseModel):
    status: str                 # success | otp_pending | blocked
    is_known_device: bool
    otp_id: Optional[str] = None
    message: str


class OTPVerifyRequest(BaseModel):
    otp_id: str
    code: str


class SignupEventOut(BaseModel):
    id: str
    email: str
    ip_address: str
    ip_type: Optional[str]
    fingerprint: str
    risk_score: float
    decision: str
    reasons: Any
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceOut(BaseModel):
    id: str
    fingerprint: str
    label: str
    trust_score: float
    is_trusted: bool
    last_seen_ip: Optional[str]
    last_seen_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    total_signups: int
    allowed: int
    flagged: int
    blocked: int
    total_devices: int
    trusted_devices: int


class AccountOut(BaseModel):
    id: str
    email: str
    created_at: datetime
    devices: List[DeviceOut] = []

    class Config:
        from_attributes = True
