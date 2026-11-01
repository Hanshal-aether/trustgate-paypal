"""
Hybrid scoring: rules + ML.

Design decision (defend this in Q&A): final risk = MAX(rule_score, ml_score).
Either system can raise the alarm, neither can silence the other. Rules catch blatant abuse with zero latency and
full explainability; ML adds learned patterns (identity velocity, email-domain rarity) the rules don't encode.
Weights are not averaged because we have no real signup labels yet to tune a blend honestly.
"""
from typing import Optional

from app import scoring, ml_scoring


def score_signup_hybrid(email: str, ip_address: str, fingerprint: str, user_agent: Optional[str] = None) -> dict:
    rule = scoring.score_signup(email, ip_address, fingerprint)
    ml = ml_scoring.score_event(email, fingerprint, user_agent)

    final = rule["risk_score"]
    reasons = list(rule["reasons"])
    ml_score = None
    if ml is not None:
        ml_score = ml["risk_score"]
        final = max(final, ml_score)
        if reasons == ["no_risk_signals_detected"] and ml["reasons"]:
            reasons = []
        reasons += ml["reasons"]

    if final >= scoring.BLOCK_THRESHOLD:
        decision = "block"
    elif final >= scoring.FLAG_THRESHOLD:
        decision = "flag"
    else:
        decision = "allow"

    return {
        "risk_score": round(final, 1),
        "decision": decision,
        "reasons": reasons,
        "ip_type": rule["ip_type"],
        "rule_score": rule["risk_score"],
        "ml_score": ml_score,
        "ml_enabled": ml is not None,
    }
