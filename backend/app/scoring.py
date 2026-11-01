"""
Rule-based risk scoring engine (Module 1 - v1 "story").

Design note: every signal here is independently weak (an email provider
alone, an IP alone, proves nothing) - the point of the engine is combining
several weak signals into one score, the same way real fraud systems do.
This file is intentionally the most "explain this in the judge Q&A" part
of the codebase - every weight below is a judgment call you should be able
to defend, not a magic number.

IP reputation: a production system calls a real IP-intelligence API
(IPQualityScore, ipinfo.io, etc). For a hackathon demo that must work on
flaky venue wifi with zero external dependencies, we ship a small local
heuristic list of known hosting/datacenter CIDR prefixes instead. This is
a deliberate reliability trade-off, documented here and in the README -
swapping in a real API is a one-function change (see classify_ip).
"""
from app.redis_client import record_and_count

from app.disposable import DISPOSABLE_DOMAINS as DISPOSABLE_EMAIL_DOMAINS  # ~9.9k domains, CC0 list

# Illustrative known datacenter/hosting prefixes (AWS/GCP/Azure/common VPN
# exit ranges, abbreviated for demo purposes). Real system -> real API.
DATACENTER_PREFIXES = (
    "3.", "13.", "18.", "34.", "35.", "52.", "54.",     # AWS-ish
    "104.154.", "104.196.", "35.184.",                   # GCP-ish
    "13.64.", "40.", "52.1", "104.40.",                  # Azure-ish
)

WEIGHTS = {
    "disposable_email": 30,
    "datacenter_ip": 25,
    "fingerprint_velocity": 25,   # same fingerprint signing up repeatedly
    "ip_velocity": 20,            # same IP signing up repeatedly
}

FLAG_THRESHOLD = 40
BLOCK_THRESHOLD = 70


def classify_ip(ip_address: str) -> str:
    if any(ip_address.startswith(p) for p in DATACENTER_PREFIXES):
        return "hosting"
    return "residential"


def is_disposable_email(email: str) -> bool:
    domain = email.split("@")[-1].lower().strip()
    return domain in DISPOSABLE_EMAIL_DOMAINS


def score_signup(email: str, ip_address: str, fingerprint: str) -> dict:
    reasons = []
    score = 0

    if is_disposable_email(email):
        score += WEIGHTS["disposable_email"]
        reasons.append("disposable_email_domain")

    ip_type = classify_ip(ip_address)
    if ip_type == "hosting":
        score += WEIGHTS["datacenter_ip"]
        reasons.append("datacenter_or_vpn_ip")

    fp_count = record_and_count(f"fp:{fingerprint}", window_seconds=600)
    if fp_count > 1:
        # first occurrence doesn't count against it; repeats do, scaling up
        extra = min(fp_count - 1, 4) * (WEIGHTS["fingerprint_velocity"] / 4)
        score += extra
        reasons.append(f"fingerprint_reused_{fp_count}x_in_10min")

    ip_count = record_and_count(f"ip:{ip_address}", window_seconds=600)
    if ip_count > 2:
        extra = min(ip_count - 2, 4) * (WEIGHTS["ip_velocity"] / 4)
        score += extra
        reasons.append(f"ip_signup_burst_{ip_count}x_in_10min")

    score = round(min(score, 100), 1)

    if score >= BLOCK_THRESHOLD:
        decision = "block"
    elif score >= FLAG_THRESHOLD:
        decision = "flag"
    else:
        decision = "allow"

    if not reasons:
        reasons.append("no_risk_signals_detected")

    return {
        "risk_score": score,
        "decision": decision,
        "reasons": reasons,
        "ip_type": ip_type,
    }
