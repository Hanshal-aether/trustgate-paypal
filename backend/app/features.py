"""Email-derived features shared by training (training/train.py) and serving (ml_scoring.py).
One implementation for both sides is what prevents train/serve skew."""
from app.disposable import DISPOSABLE_DOMAINS


def split_email(email: str):
    local, _, domain = email.strip().lower().partition("@")
    return local, domain


def email_features(email: str, domain_freq: dict) -> dict:
    local, domain = split_email(email)
    n = max(len(local), 1)
    return {
        "email_disposable": 1.0 if domain in DISPOSABLE_DOMAINS else 0.0,
        "email_domain_freq": float(domain_freq.get(domain, 0.0)),     # unseen domain -> 0 (rare = riskier)
        "email_local_len": float(len(local)),
        "email_local_digit_ratio": sum(c.isdigit() for c in local) / n,
    }
