"""
PayPal-centred free-trial flow for the demo SaaS ("CloudNotes").

1. start-trial        TrustGate scores the signup first (rules + model). Block stops here, PayPal is never called.
2. verify-challenge   Flagged signups must pass a one-time code, then continue.
3. (buyer approves the subscription on PayPal Sandbox)
4. confirm            We read the subscription from PayPal. If that PayPal account already holds another free trial,
                      TrustGate cancels the new subscription through the PayPal API: repeat-trial abuse caught by payer identity.
5. webhook            Optional. PayPal tells us about cancellations so statuses stay in sync.

confirm is called by the browser when PayPal sends the buyer back, so the whole flow works on localhost without a public webhook URL.
"""
import os
import random
import string
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.paypal_client import PayPalClient, PayPalError, from_env
from app.paypal_models import AppSetting, TrialSubscription
from app.routers.signup import signup_check

router = APIRouter(prefix="/api/paypal", tags=["paypal"])
_client: Optional[PayPalClient] = None


def get_client() -> PayPalClient:
    global _client
    if _client is None:
        _client = from_env()
    return _client


def web_url() -> str:
    return os.getenv("PUBLIC_WEB_URL", "http://localhost:4173").rstrip("/")


def ensure_plan(db: Session, pp: PayPalClient) -> str:
    env_plan = os.getenv("PAYPAL_PLAN_ID", "").strip()
    if env_plan:
        return env_plan
    row = db.get(AppSetting, "paypal_plan_id")
    if row:
        return row.value
    product_id = pp.create_product("CloudNotes Pro (TrustGate demo)")
    plan_id = pp.create_plan(product_id, "CloudNotes Pro, 7-day free trial")
    db.add(AppSetting(key="paypal_plan_id", value=plan_id))
    db.commit()
    return plan_id


def _start_paypal(db: Session, pp: PayPalClient, trial: TrialSubscription) -> dict:
    if not pp.configured:
        raise HTTPException(503, "PayPal is not set up on this server. Add PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET (see README_PAYPAL.md).")
    try:
        plan_id = ensure_plan(db, pp)
        sub = pp.create_subscription(plan_id, f"{web_url()}/?paypal=return", f"{web_url()}/?paypal=cancel", custom_id=trial.id)
    except PayPalError as e:
        raise HTTPException(502, str(e))
    trial.paypal_subscription_id = sub["id"]
    trial.status = "awaiting_paypal"
    db.add(trial)
    db.commit()
    return {"subscription_id": sub["id"], "approval_url": sub["approve_url"]}


def _result(t: TrialSubscription, **extra) -> dict:
    return {"status": t.status, "trial_id": t.id, "email": t.email, "payer_email": t.paypal_payer_email,
            "decision": t.decision, "risk_score": t.risk_score, "reasons": t.reasons or [], **extra}


class StartTrial(BaseModel):
    email: str
    fingerprint: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class VerifyBody(BaseModel):
    trial_id: str
    code: str


class ConfirmBody(BaseModel):
    subscription_id: str


@router.get("/status")
def status(db: Session = Depends(get_db), pp: PayPalClient = Depends(get_client)):
    return {"configured": pp.configured, "mode": pp.mode,
            "plan_ready": bool(os.getenv("PAYPAL_PLAN_ID") or db.get(AppSetting, "paypal_plan_id")),
            "webhook_verification": bool(os.getenv("PAYPAL_WEBHOOK_ID"))}


@router.post("/reset")
def reset_plan(db: Session = Depends(get_db)):
    """Forget the cached plan (use after switching to a different PayPal app)."""
    row = db.get(AppSetting, "paypal_plan_id")
    if row:
        db.delete(row)
        db.commit()
    return {"reset": True}


@router.post("/start-trial")
def start_trial(payload: StartTrial, request: Request, db: Session = Depends(get_db), pp: PayPalClient = Depends(get_client)):
    ip = payload.ip_address or (request.client.host if request.client else "0.0.0.0")
    scored = signup_check(schemas.SignupCheckRequest(email=payload.email, ip_address=ip,
                                                     fingerprint=payload.fingerprint, user_agent=payload.user_agent), db)
    trial = TrialSubscription(email=payload.email, fingerprint=payload.fingerprint, ip_address=ip,
                              risk_score=scored.risk_score, decision=scored.decision, reasons=scored.reasons)
    base = {"decision": scored.decision, "risk_score": scored.risk_score, "reasons": scored.reasons,
            "rule_score": scored.rule_score, "ml_score": scored.ml_score}

    if scored.decision == "block":
        trial.status = "blocked"
        db.add(trial)
        db.commit()
        return {**base, "trial_id": trial.id}

    if scored.decision == "flag":
        code = "".join(random.choices(string.digits, k=6))
        trial.status = "challenged"
        trial.challenge_code = code
        trial.challenge_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.add(trial)
        db.commit()
        # demo only: a real product sends this code to the customer's email or phone, never back to the browser
        return {**base, "trial_id": trial.id, "challenge": {"demo_code": code}}

    db.add(trial)
    db.flush()
    return {**base, "trial_id": trial.id, **_start_paypal(db, pp, trial)}


@router.post("/verify-challenge")
def verify_challenge(body: VerifyBody, db: Session = Depends(get_db), pp: PayPalClient = Depends(get_client)):
    t = db.get(TrialSubscription, body.trial_id)
    if not t or t.status != "challenged":
        raise HTTPException(404, "There is no pending check for this trial.")
    if t.challenge_expires_at and datetime.utcnow() > t.challenge_expires_at:
        raise HTTPException(400, "That code expired. Start again.")
    if t.challenge_code != body.code:
        raise HTTPException(400, "That code is not right.")
    t.challenge_code = None
    return {"trial_id": t.id, **_start_paypal(db, pp, t)}


@router.post("/confirm")
def confirm(body: ConfirmBody, db: Session = Depends(get_db), pp: PayPalClient = Depends(get_client)):
    t = db.query(TrialSubscription).filter(TrialSubscription.paypal_subscription_id == body.subscription_id).first()
    if not t:
        raise HTTPException(404, "Unknown subscription.")
    if t.status in ("active", "cancelled_abuse", "cancelled"):
        return _result(t)          # safe to call twice, e.g. when the page is refreshed
    try:
        sub = pp.get_subscription(body.subscription_id)
    except PayPalError as e:
        raise HTTPException(502, str(e))

    subscriber = sub.get("subscriber") or {}
    t.paypal_payer_id = subscriber.get("payer_id")
    t.paypal_payer_email = subscriber.get("email_address")
    if sub.get("status") not in ("ACTIVE", "APPROVED"):
        db.commit()
        return _result(t, status="pending", paypal_status=sub.get("status"))

    other = None
    if t.paypal_payer_id:
        other = (db.query(TrialSubscription)
                 .filter(TrialSubscription.paypal_payer_id == t.paypal_payer_id, TrialSubscription.id != t.id,
                         TrialSubscription.status == "active").first())
    if other:
        cancel_ok = True
        try:
            pp.cancel_subscription(body.subscription_id, "TrustGate: this PayPal account already has a free trial")
        except PayPalError:
            cancel_ok = False
        t.status = "cancelled_abuse"
        t.decision, t.risk_score = "block", 100.0
        t.reasons = list(t.reasons or []) + ["paypal_payer_reused"]
        db.add(models.SignupEvent(email=t.email, ip_address=t.ip_address, ip_type="residential", fingerprint=t.fingerprint,
                                  risk_score=100.0, decision="block", reasons=["paypal_payer_reused"]))
        db.commit()
        return _result(t, cancelled_via_api=cancel_ok, first_trial_email=other.email)

    t.status = "active"
    db.commit()
    return _result(t)


@router.post("/webhook")
async def webhook(request: Request, db: Session = Depends(get_db), pp: PayPalClient = Depends(get_client)):
    event = await request.json()
    webhook_id = os.getenv("PAYPAL_WEBHOOK_ID", "").strip()
    if webhook_id:
        try:
            ok = pp.verify_webhook(dict(request.headers), event, webhook_id)
        except PayPalError:
            ok = False
        if not ok:
            raise HTTPException(400, "Webhook signature could not be verified.")
    if event.get("event_type") in ("BILLING.SUBSCRIPTION.CANCELLED", "BILLING.SUBSCRIPTION.EXPIRED", "BILLING.SUBSCRIPTION.SUSPENDED"):
        sub_id = (event.get("resource") or {}).get("id")
        t = db.query(TrialSubscription).filter(TrialSubscription.paypal_subscription_id == sub_id).first()
        if t and t.status == "active":
            t.status = "cancelled"
            db.commit()
    return {"received": True}


@router.get("/trials")
def trials(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(TrialSubscription).order_by(TrialSubscription.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "email": r.email, "decision": r.decision, "risk_score": r.risk_score, "status": r.status,
             "reasons": r.reasons or [], "paypal_subscription_id": r.paypal_subscription_id,
             "payer_email": r.paypal_payer_email, "created_at": r.created_at.isoformat()} for r in rows]
