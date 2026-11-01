"""
"Simulate Attack" endpoint - lets a judge trigger a realistic abuse pattern
with one click instead of you manually faking requests during a live demo.
Fires several signups reusing the same fingerprint (classic multi-account
abuse) and one legitimate signup for contrast, so the dashboard visibly
shows the system telling good and bad traffic apart in real time.
"""
import random
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, hybrid

router = APIRouter(prefix="/api/demo", tags=["demo"])

FAKE_NAMES = ["alex", "sam", "jordan", "taylor", "casey", "morgan"]
ATTACK_FINGERPRINT = "fp_demo_attacker_device_001"
ATTACK_IP = "3.120.44.19"  # falls in our demo "hosting" range


@router.post("/simulate-attack")
def simulate_attack(db: Session = Depends(get_db)):
    created = []
    # 4 abuse signups: same fingerprint + datacenter IP, rapid-fire
    for i in range(4):
        email = f"{random.choice(FAKE_NAMES)}{random.randint(100,999)}@mailinator.com"
        result = hybrid.score_signup_hybrid(email, ATTACK_IP, ATTACK_FINGERPRINT)
        event = models.SignupEvent(
            email=email, ip_address=ATTACK_IP, ip_type=result["ip_type"],
            fingerprint=ATTACK_FINGERPRINT, risk_score=result["risk_score"],
            decision=result["decision"], reasons=result["reasons"],
        )
        db.add(event)
        created.append({"email": email, "decision": result["decision"], "score": result["risk_score"]})

    # 1 legitimate signup for contrast
    good_email = f"real.user.{random.randint(1000,9999)}@gmail.com"
    good_result = hybrid.score_signup_hybrid(good_email, "49.207.12.88", f"fp_real_{random.randint(1,999)}")
    good_event = models.SignupEvent(
        email=good_email, ip_address="49.207.12.88", ip_type=good_result["ip_type"],
        fingerprint=f"fp_real_{random.randint(1,999)}", risk_score=good_result["risk_score"],
        decision=good_result["decision"], reasons=good_result["reasons"],
    )
    db.add(good_event)
    created.append({"email": good_email, "decision": good_result["decision"], "score": good_result["risk_score"]})

    db.commit()
    return {"simulated_events": created}
