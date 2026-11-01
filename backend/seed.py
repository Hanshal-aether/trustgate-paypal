"""
Seeds realistic-looking demo data so the dashboard isn't empty on first load.
This is DEMO UI DATA ONLY (synthetic, invented) and is separate from the model's synthetic
training data in /training. See MODEL_CARD.md.

Run: python seed.py  (from inside backend/, with venv active or in container)
"""
import random
from datetime import datetime, timedelta

from app.database import Base, engine, SessionLocal
from app import models, scoring

Base.metadata.create_all(bind=engine)
db = SessionLocal()

GOOD_DOMAINS = ["gmail.com", "outlook.com", "yahoo.com", "proton.me"]
BAD_DOMAINS = ["mailinator.com", "yopmail.com", "guerrillamail.com"]
GOOD_IPS = ["49.207.{}.{}", "103.21.{}.{}", "117.198.{}.{}"]
BAD_IPS = ["3.120.{}.{}", "13.64.{}.{}", "52.1.{}.{}"]


def rand_ip(template):
    n_slots = template.count("{}")
    return template.format(*[random.randint(1, 254) for _ in range(n_slots)])


def seed_signups(n=40):
    for i in range(n):
        is_bad = random.random() < 0.25
        if is_bad:
            email = f"user{random.randint(1000,9999)}@{random.choice(BAD_DOMAINS)}"
            ip = rand_ip(random.choice(BAD_IPS))
            fingerprint = f"fp_shared_{random.randint(1,5)}"  # reused on purpose
        else:
            email = f"person{random.randint(1000,9999)}@{random.choice(GOOD_DOMAINS)}"
            ip = rand_ip(random.choice(GOOD_IPS))
            fingerprint = f"fp_unique_{i}"

        result = scoring.score_signup(email, ip, fingerprint)
        event = models.SignupEvent(
            email=email, ip_address=ip, ip_type=result["ip_type"],
            fingerprint=fingerprint, risk_score=result["risk_score"],
            decision=result["decision"], reasons=result["reasons"],
            created_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 600)),
        )
        db.add(event)
    db.commit()
    print(f"Seeded {n} signup events.")


def seed_devices_and_accounts(n=8):
    for i in range(n):
        account = models.Account(email=f"customer{i}@gmail.com")
        db.add(account)
        db.flush()
        trust = random.choice([30, 55, 85, 95])
        device = models.Device(
            account_id=account.id,
            fingerprint=f"fp_cust_{i}",
            label=f"{'Laptop' if i % 2 == 0 else 'Phone'} - customer{i}",
            trust_score=trust,
            is_trusted=trust >= 80,
            first_seen_ip=rand_ip(random.choice(GOOD_IPS)),
            last_seen_ip=rand_ip(random.choice(GOOD_IPS)),
        )
        db.add(device)
    db.commit()
    print(f"Seeded {n} accounts + devices.")


if __name__ == "__main__":
    seed_signups()
    seed_devices_and_accounts()
    print("Seed complete.")
