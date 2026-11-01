"""Synthetic signup-abuse data generator.

EVERYTHING here is invented by us: no real users, no third-party dataset. The model trained on it therefore learns
OUR assumptions about how abusers behave. Metrics on this data measure "does the pipeline work and does the model
recover the patterns we simulated", NOT real-world fraud-catching accuracy. The README and model card say so.

Simulated behaviours (all assumptions, tune freely):
  * honest users: mostly one signup per device, name-like email, big mail providers or company domains; ~1.5% use a
    disposable address for privacy; ~4% share a device with a family member / colleague (repeat fingerprint).
  * abusers (~8% of signups): free-trial farming campaigns of 2-12 signups, auto-generated emails with many digits,
    often disposable domains; 25% rotate their fingerprint every signup (velocity features can't see them).
  * drift: in the last 20% of the timeline abusers adapt (fewer disposable domains, more name-like gmail addresses),
    so the time-based test set is harder than the training set - like real life.
"""
import numpy as np
import pandas as pd

MAJOR = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "icloud.com", "proton.me"]
MAJOR_P = [0.56, 0.14, 0.12, 0.08, 0.07, 0.03]
FIRST = ["aarav", "vivaan", "diya", "anaya", "rohan", "meera", "arjun", "kavya", "sana", "imran", "neha", "karan",
         "priya", "rahul", "sneha", "amit", "pooja", "vikram", "isha", "zoya", "john", "emma", "liam", "olivia"]
LAST = ["sharma", "verma", "khan", "reddy", "patel", "gupta", "singh", "iyer", "nair", "das", "smith", "brown"]
SEP = ["", ".", "_"]


def _name_local(r):
    s = r.choice(FIRST) + r.choice(SEP) + r.choice(LAST)
    return s + (str(r.integers(1, 99)) if r.random() < 0.25 else "")


def _junk_local(r):
    n = int(r.integers(7, 14))
    chars = list("abcdefghijklmnopqrstuvwxyz0123456789")
    return "".join(r.choice(chars) for _ in range(n))


def generate(n=150_000, seed=42, disposable_domains=None):
    r = np.random.default_rng(seed)
    disp = sorted(disposable_domains) if disposable_domains else ["mailinator.com"]
    company = [f"{w}{r.integers(1, 400)}.{t}" for w in ["tech", "labs", "corp", "studio", "soft", "data", "mail", "works"]
               for t in ["com", "io", "in", "co"]]
    span = 30 * 86400.0
    rows, fp_id = [], 0
    t_drift = 0.8 * span

    def new_fp():
        nonlocal fp_id
        fp_id += 1
        return f"fp{fp_id}"

    honest_fps = []
    n_honest = int(n * 0.92)
    for _ in range(n_honest):
        t = r.random() * span
        if honest_fps and r.random() < 0.04:
            fp = honest_fps[r.integers(len(honest_fps))]               # shared device (family / office)
        else:
            fp = new_fp(); honest_fps.append(fp)
        u = r.random()
        if u < 0.015:
            dom = disp[r.integers(len(disp))]                          # privacy-minded honest user
        elif u < 0.70:
            dom = r.choice(MAJOR, p=MAJOR_P)
        else:
            dom = company[r.integers(len(company))]
        local = _name_local(r) if r.random() < 0.93 else _junk_local(r)
        dev = r.choice([0.0, 1.0, np.nan], p=[0.50, 0.45, 0.05])
        rows.append((t, fp, f"{local}@{dom}", dev, 0))

    n_abuse = n - n_honest
    made = 0
    while made < n_abuse:
        k = int(r.integers(2, 13))
        t0 = r.random() * span
        drifted = t0 >= t_drift
        rotate = r.random() < 0.25
        fp = new_fp()
        t = t0
        for _ in range(k):
            if rotate:
                fp = new_fp()
            p_disp = 0.30 if drifted else 0.55
            u = r.random()
            if u < p_disp:
                dom = disp[r.integers(len(disp))]
            elif u < p_disp + 0.35:
                dom = "gmail.com"
            else:
                dom = r.choice(MAJOR, p=MAJOR_P)
            p_name = 0.55 if drifted else 0.12                         # adaptation: look like a person
            local = _name_local(r) if r.random() < p_name else _junk_local(r)
            dev = r.choice([0.0, 1.0, np.nan], p=[0.70, 0.25, 0.05])
            rows.append((t, fp, f"{local}@{dom}", dev, 1))
            t += float(r.exponential(300.0 if r.random() < 0.8 else 7200.0))
            made += 1
            if made >= n_abuse:
                break
    df = pd.DataFrame(rows, columns=["ts", "fingerprint", "email", "device_type", "label"])
    return df.sort_values("ts", kind="mergesort").reset_index(drop=True)


def add_velocity(df):
    """Same four numbers app.redis_client.identity_history serves, computed in time order per fingerprint."""
    df = df.copy()
    g = df.groupby("fingerprint")
    df["idn_n_prev"] = g.cumcount().astype(float)
    prev = g["ts"].shift(1)
    df["idn_secs_since_prev"] = df["ts"] - prev                       # NaN for first sighting
    hb = (df["ts"] // 3600).astype(int)
    db = (df["ts"] // 86400).astype(int)
    df["idn_same_hour"] = df.groupby(["fingerprint", hb]).cumcount().astype(float)
    df["idn_same_day"] = df.groupby(["fingerprint", db]).cumcount().astype(float)
    return df
