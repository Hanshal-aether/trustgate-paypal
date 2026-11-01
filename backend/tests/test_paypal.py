"""Run:  docker compose exec backend pytest -q tests/test_paypal.py
These tests use a FAKE PayPal server (httpx.MockTransport), so they never touch the network.
The first live test against the real PayPal Sandbox is yours: see README_PAYPAL.md."""
import json
import os
import random
import re
import uuid

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_paypal.db")

import httpx
import pytest
from fastapi.testclient import TestClient

from app.paypal_client import PayPalClient


def fake_paypal(payer=None, sub_status="ACTIVE"):
    calls, bodies = [], {}
    payer = payer or f"PAYER-{uuid.uuid4().hex[:8]}"

    def handler(request: httpx.Request):
        p = request.url.path
        calls.append((request.method, p))
        if request.content:
            try:
                bodies[p] = json.loads(request.content)
            except ValueError:
                pass
        if p == "/v1/oauth2/token":
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 3000})
        if p == "/v1/catalogs/products":
            return httpx.Response(201, json={"id": "PROD-1"})
        if p == "/v1/billing/plans":
            return httpx.Response(201, json={"id": "P-TEST"})
        if p == "/v1/billing/subscriptions" and request.method == "POST":
            sid = f"I-{uuid.uuid4().hex[:10]}"
            return httpx.Response(201, json={"id": sid, "status": "APPROVAL_PENDING",
                                             "links": [{"rel": "approve", "href": f"https://www.sandbox.paypal.com/webapps/billing/subscriptions?ba_token=BA-{sid}"}]})
        if p.endswith("/cancel"):
            return httpx.Response(204)
        if p.startswith("/v1/billing/subscriptions/"):
            return httpx.Response(200, json={"id": p.split("/")[-1], "status": sub_status,
                                             "subscriber": {"payer_id": payer, "email_address": "sandbox.buyer@example.com"}})
        return httpx.Response(404, json={})

    return PayPalClient("id", "secret", transport=httpx.MockTransport(handler)), calls, bodies


@pytest.fixture()
def api(monkeypatch):
    from app.main import app
    from app.routers import paypal
    from app import ml_scoring
    # These tests cover the PayPal flow, so they use the deterministic rule engine only.
    # The model has its own tests in test_ml_scoring.py.
    monkeypatch.setattr(ml_scoring, "ML_AVAILABLE", False)

    def make(pp):
        app.dependency_overrides[paypal.get_client] = lambda: pp
        return TestClient(app)

    yield make
    app.dependency_overrides.pop(paypal.get_client, None)


def email():
    return f"{random.choice(['asha','rohan','meera','karan','zoya'])}.{random.choice(['rao','nair','shah','iyer','bose'])}@gmail.com"


def dc_ip():
    return f"3.{random.randint(1, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"


def start(c, em=None, ip="49.207.12.88", fp=None):
    return c.post("/api/paypal/start-trial", json={"email": em or email(), "ip_address": ip,
                                                    "fingerprint": fp or f"fp_{uuid.uuid4().hex[:10]}"}).json()


def test_status_reports_not_configured(api):
    c = api(PayPalClient("", ""))
    body = c.get("/api/paypal/status").json()
    assert body["configured"] is False and body["mode"] == "sandbox"


def test_not_configured_clear_error_for_clean_signup(api):
    c = api(PayPalClient("", ""))
    r = c.post("/api/paypal/start-trial", json={"email": email(), "ip_address": "49.207.12.88", "fingerprint": "fp_nc_" + uuid.uuid4().hex[:6]})
    assert r.status_code == 503 and "PAYPAL_CLIENT_ID" in r.json()["detail"]


def test_client_builds_trial_then_regular_plan_and_caches_token(api):
    pp, calls, bodies = fake_paypal()
    pp.create_plan("PROD-1", "Plan", trial_days=7, price="9.99")
    pp.create_product("x")
    cycles = bodies["/v1/billing/plans"]["billing_cycles"]
    assert [c["tenure_type"] for c in cycles] == ["TRIAL", "REGULAR"]
    assert cycles[0]["pricing_scheme"]["fixed_price"]["value"] == "0" and cycles[0]["frequency"]["interval_count"] == 7
    assert sum(1 for m, p in calls if p == "/v1/oauth2/token") == 1   # token reused for the second request


def test_block_never_calls_paypal(api):
    pp, calls, _ = fake_paypal()
    c = api(pp)
    fp, ip = f"fp_{uuid.uuid4().hex[:8]}", dc_ip()
    decisions = [start(c, f"x{i}@mailinator.com", ip, fp)["decision"] for i in range(8)]
    assert "block" in decisions
    assert not any(m == "POST" and p == "/v1/billing/subscriptions" for m, p in calls)


def test_clean_signup_gets_a_paypal_approval_link(api):
    pp, calls, bodies = fake_paypal()
    out = start(api(pp))
    assert out["decision"] == "allow" and out["approval_url"].startswith("https://www.sandbox.paypal.com/")
    assert out["subscription_id"].startswith("I-")
    assert bodies["/v1/billing/subscriptions"]["plan_id"] in ("P-TEST",) or bodies["/v1/billing/subscriptions"]["plan_id"]


def test_flagged_signup_needs_the_code_then_continues(api):
    pp, calls, _ = fake_paypal()
    c = api(pp)
    out = start(c, "flagme_" + uuid.uuid4().hex[:6] + "@mailinator.com", dc_ip())
    assert out["decision"] == "flag" and len(out["challenge"]["demo_code"]) == 6 and "approval_url" not in out
    assert c.post("/api/paypal/verify-challenge", json={"trial_id": out["trial_id"], "code": "000000"}).status_code == 400
    ok = c.post("/api/paypal/verify-challenge", json={"trial_id": out["trial_id"], "code": out["challenge"]["demo_code"]}).json()
    assert ok["approval_url"].startswith("https://www.sandbox.paypal.com/")


def test_same_paypal_account_cannot_run_two_free_trials(api):
    pp, calls, _ = fake_paypal()                      # the SAME fake buyer approves both subscriptions
    c = api(pp)
    first, second = start(c), start(c)
    r1 = c.post("/api/paypal/confirm", json={"subscription_id": first["subscription_id"]}).json()
    assert r1["status"] == "active"
    r2 = c.post("/api/paypal/confirm", json={"subscription_id": second["subscription_id"]}).json()
    assert r2["status"] == "cancelled_abuse" and r2["cancelled_via_api"] is True and "paypal_payer_reused" in r2["reasons"]
    assert ("POST", f"/v1/billing/subscriptions/{second['subscription_id']}/cancel") in calls
    assert ("POST", f"/v1/billing/subscriptions/{first['subscription_id']}/cancel") not in calls
    events = c.get("/api/dashboard/signups?limit=500").json()
    assert any("paypal_payer_reused" in e["reasons"] for e in events)


def test_different_paypal_accounts_both_get_trials(api):
    c1 = api(fake_paypal(payer="PAYER-A-" + uuid.uuid4().hex[:6])[0])
    a = start(c1)
    assert c1.post("/api/paypal/confirm", json={"subscription_id": a["subscription_id"]}).json()["status"] == "active"
    c2 = api(fake_paypal(payer="PAYER-B-" + uuid.uuid4().hex[:6])[0])
    b = start(c2)
    assert c2.post("/api/paypal/confirm", json={"subscription_id": b["subscription_id"]}).json()["status"] == "active"


def test_confirm_twice_is_safe_and_pending_is_reported(api):
    pp, calls, _ = fake_paypal(sub_status="APPROVAL_PENDING")
    c = api(pp)
    s = start(c)
    assert c.post("/api/paypal/confirm", json={"subscription_id": s["subscription_id"]}).json()["status"] == "pending"
    pp2, calls2, _ = fake_paypal()
    c = api(pp2)
    s = start(c)
    assert c.post("/api/paypal/confirm", json={"subscription_id": s["subscription_id"]}).json()["status"] == "active"
    n = len(calls2)
    assert c.post("/api/paypal/confirm", json={"subscription_id": s["subscription_id"]}).json()["status"] == "active"
    assert len(calls2) == n                           # second call did not hit PayPal again


def test_webhook_cancellation_updates_status_and_trials_list(api):
    pp, _, _ = fake_paypal()
    c = api(pp)
    s = start(c)
    c.post("/api/paypal/confirm", json={"subscription_id": s["subscription_id"]})
    c.post("/api/paypal/webhook", json={"event_type": "BILLING.SUBSCRIPTION.CANCELLED", "resource": {"id": s["subscription_id"]}})
    row = [t for t in c.get("/api/paypal/trials?limit=500").json() if t["paypal_subscription_id"] == s["subscription_id"]][0]
    assert row["status"] == "cancelled"
