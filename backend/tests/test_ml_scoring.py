"""Run inside the container:  docker compose exec backend pytest -q"""
import os
import uuid

os.environ["DATABASE_URL"] = "sqlite:///./test_trustgate.db"   # tests never touch the real Postgres

import pytest
from fastapi.testclient import TestClient

from app import ml_scoring, hybrid
from app.main import app

needs_model = pytest.mark.skipif(not ml_scoring.ML_AVAILABLE, reason="model files not in app/model/")


def fp():
    return f"fp_test_{uuid.uuid4().hex[:10]}"


def test_risk_score_mapping_anchors_and_monotonic():
    f, b = 0.10, 0.30
    assert ml_scoring.to_risk_score(0.0, f, b) == 0.0
    assert ml_scoring.to_risk_score(f, f, b) == pytest.approx(40.0)
    assert ml_scoring.to_risk_score(b, f, b) == pytest.approx(70.0)
    assert ml_scoring.to_risk_score(5.0, f, b) == 100.0
    xs = [i / 100 for i in range(0, 101)]
    ys = [ml_scoring.to_risk_score(x, f, b) for x in xs]
    assert ys == sorted(ys)


def test_hybrid_falls_back_to_rules_when_ml_disabled(monkeypatch):
    monkeypatch.setattr(ml_scoring, "ML_AVAILABLE", False)
    out = hybrid.score_signup_hybrid("someone@gmail.com", "49.207.12.88", fp())
    assert out["ml_enabled"] is False and out["ml_score"] is None
    assert out["decision"] in {"allow", "flag", "block"}


def test_rules_still_catch_obvious_abuse(monkeypatch):
    monkeypatch.setattr(ml_scoring, "ML_AVAILABLE", False)
    out = hybrid.score_signup_hybrid("x@mailinator.com", "3.120.44.19", fp())
    assert out["decision"] in {"flag", "block"}
    assert "disposable_email_domain" in out["reasons"]


@needs_model
def test_ml_score_in_range_with_reasons_list():
    out = ml_scoring.score_event("a@gmail.com", fp(), record=False)
    assert 0.0 <= out["risk_score"] <= 100.0
    assert 0.0 <= out["probability"] <= 1.0
    assert isinstance(out["reasons"], list)


@needs_model
def test_velocity_counts_up_and_dry_run_does_not_count():
    f = fp()
    seen = [ml_scoring.score_event("a@gmail.com", f)["features"]["idn_n_prev"] for _ in range(4)]
    assert seen == [0.0, 1.0, 2.0, 3.0]
    before = ml_scoring.score_event("a@gmail.com", f, record=False)["features"]["idn_n_prev"]
    again = ml_scoring.score_event("a@gmail.com", f, record=False)["features"]["idn_n_prev"]
    assert before == again == 4.0


@needs_model
def test_hybrid_is_max_of_rule_and_ml():
    out = hybrid.score_signup_hybrid("a@gmail.com", "49.207.12.88", fp())
    assert out["ml_enabled"] is True
    assert out["risk_score"] == pytest.approx(max(out["rule_score"], out["ml_score"]), abs=0.11)


def test_api_signup_check_and_ml_status():
    client = TestClient(app)
    r = client.post("/api/signup-check", json={"email": "t@gmail.com", "ip_address": "49.207.12.88", "fingerprint": fp()})
    assert r.status_code == 200
    body = r.json()
    assert body["decision"] in {"allow", "flag", "block"} and "ml_enabled" in body
    s = client.get("/api/ml/status")
    assert s.status_code == 200 and "ml_enabled" in s.json()


def test_new_device_becomes_trusted_after_otp_and_skips_otp_next_time():
    import re
    from app.database import SessionLocal
    from app import models
    email = f"owner_{uuid.uuid4().hex[:8]}@gmail.com"
    db = SessionLocal(); db.add(models.Account(email=email)); db.commit(); db.close()

    client = TestClient(app)
    body = {"email": email, "ip_address": "49.207.12.88", "fingerprint": fp()}

    first = client.post("/api/login-check", json=body).json()
    assert first["status"] == "otp_pending"                       # unknown device -> challenge
    code = re.search(r"DEMO CODE: (\d+)", first["message"]).group(1)
    assert client.post("/api/otp/verify", json={"otp_id": first["otp_id"], "code": code}).status_code == 200

    second = client.post("/api/login-check", json=body).json()
    assert second["status"] == "success" and second["is_known_device"] is True   # now remembered

    wrong = {**body, "fingerprint": fp()}                           # a DIFFERENT device is still challenged
    assert client.post("/api/login-check", json=wrong).json()["status"] == "otp_pending"


def test_accounts_endpoint_lists_accounts_with_devices():
    from app.database import SessionLocal
    from app import models
    email = f"acct_{uuid.uuid4().hex[:8]}@gmail.com"
    db = SessionLocal()
    a = models.Account(email=email); db.add(a); db.flush()
    db.add(models.Device(account_id=a.id, fingerprint=fp(), label="Laptop", trust_score=90.0, is_trusted=True, last_seen_ip="49.207.12.88"))
    db.commit(); db.close()
    body = TestClient(app).get("/api/dashboard/accounts?limit=500").json()
    mine = [x for x in body if x["email"] == email][0]
    assert mine["devices"][0]["label"] == "Laptop" and mine["devices"][0]["is_trusted"] is True


def test_trust_is_lost_when_a_trusted_device_logs_in_from_far_away():
    import re
    from app.database import SessionLocal
    from app import models
    email = f"far_{uuid.uuid4().hex[:8]}@gmail.com"
    db = SessionLocal(); db.add(models.Account(email=email)); db.commit(); db.close()
    c = TestClient(app)
    home = {"email": email, "ip_address": "49.207.12.88", "fingerprint": fp()}
    r = c.post("/api/login-check", json=home).json()
    code = re.search(r"DEMO CODE: (\d+)", r["message"]).group(1)
    c.post("/api/otp/verify", json={"otp_id": r["otp_id"], "code": code})
    assert c.post("/api/login-check", json=home).json()["status"] == "success"      # trusted at home

    away = {**home, "ip_address": "198.51.100.23"}                                    # same device, far-away network
    assert c.post("/api/login-check", json=away).json()["status"] == "otp_pending"    # challenged
    dev = [d for a in c.get("/api/dashboard/accounts?limit=500").json() if a["email"] == email for d in a["devices"]][0]
    assert dev["trust_score"] == 75.0 and dev["is_trusted"] is False   # 80 +5 (home login) -10 (far away): below 80, so no longer trusted


@needs_model
def test_train_serve_parity_on_synthetic_events():
    """Features computed in training (pandas) must equal what the API computes event by event."""
    import sys
    from pathlib import Path
    import numpy as np
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "training"))
    from generate_synthetic import generate, add_velocity
    from app.disposable import DISPOSABLE_DOMAINS
    df = add_velocity(generate(n=3000, seed=7, disposable_domains=DISPOSABLE_DOMAINS))
    salt = uuid.uuid4().hex[:6]
    for r in df.head(600).itertuples():
        ua = None if np.isnan(r.device_type) else ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148" if r.device_type == 1.0 else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
        f = ml_scoring.build_features(r.email, f"{salt}{r.fingerprint}", ua, now=1_699_920_000 + r.ts, record=True)
        assert f["idn_n_prev"] == r.idn_n_prev
        assert f["idn_same_hour"] == r.idn_same_hour and f["idn_same_day"] == r.idn_same_day
        if r.idn_n_prev > 0:
            assert f["idn_secs_since_prev"] == pytest.approx(r.idn_secs_since_prev, abs=1e-3)


@needs_model
def test_honest_signup_allowed_and_obvious_farm_caught():
    ok = hybrid.score_signup_hybrid("priya.sharma@gmail.com", "49.207.12.88", fp(),
                                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36")
    assert ok["decision"] == "allow", ok
    f = fp(); last = None
    for i in range(5):
        last = hybrid.score_signup_hybrid(f"x9k2m{i}q81z@mailinator.com", "3.120.44.19", f)
    assert last["decision"] == "block" and last["ml_enabled"] is True
