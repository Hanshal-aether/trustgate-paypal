"""Train the TrustGate signup model on SYNTHETIC data and export it for the API.

Run from the repo root:   python training/train.py
Outputs: backend/app/model/trustgate_lgb.txt, backend/app/model/model_meta.json
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, roc_auc_score, roc_curve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(Path(__file__).parent))
from app.disposable import DISPOSABLE_DOMAINS          # noqa: E402
from app.features import email_features                 # noqa: E402
from generate_synthetic import generate, add_velocity   # noqa: E402

SEED = 42
FEATURES = ["email_disposable", "email_domain_freq", "email_local_len", "email_local_digit_ratio", "device_type",
            "idn_n_prev", "idn_secs_since_prev", "idn_same_hour", "idn_same_day"]
REASON_TEXT = {
    "email_disposable": "email domain is on the disposable-email list",
    "email_domain_freq": "email domain pattern linked to abuse in training data",
    "email_local_len": "unusual email name length",
    "email_local_digit_ratio": "email name looks auto-generated (many digits)",
    "device_type": "device type pattern linked to abuse in training data",
    "idn_n_prev": "this device has signed up before",
    "idn_secs_since_prev": "very short gap since this device's last signup",
    "idn_same_hour": "several signups from this device within an hour",
    "idn_same_day": "several signups from this device today",
}


def recall_at_fpr(y, p, fpr_target):
    fpr, tpr, _ = roc_curve(y, p)
    return float(np.max(tpr[fpr <= fpr_target]))


def main(n=150_000):
    df = add_velocity(generate(n=n, seed=SEED, disposable_domains=DISPOSABLE_DOMAINS))
    n_tr, n_va = int(0.6 * len(df)), int(0.8 * len(df))            # time-ordered 60/20/20 split
    train, valid, test = df.iloc[:n_tr], df.iloc[n_tr:n_va], df.iloc[n_va:]

    domains = train["email"].str.split("@").str[1]
    domain_freq = (domains.value_counts() / len(train)).round(8).to_dict()   # learned on TRAIN only

    def matrix(d):
        ef = pd.DataFrame([email_features(e, domain_freq) for e in d["email"]], index=d.index)
        x = pd.concat([ef, d[["device_type", "idn_n_prev", "idn_secs_since_prev", "idn_same_hour", "idn_same_day"]]], axis=1)
        return x[FEATURES]

    Xtr, Xva, Xte = matrix(train), matrix(valid), matrix(test)
    params = dict(objective="binary", learning_rate=0.05, num_leaves=31, min_data_in_leaf=50, feature_fraction=0.9,
                  bagging_fraction=0.8, bagging_freq=1, seed=SEED, verbose=-1, deterministic=True, num_threads=2)
    booster = lgb.train(params, lgb.Dataset(Xtr, train["label"]), num_boost_round=600,
                        valid_sets=[lgb.Dataset(Xva, valid["label"])],
                        callbacks=[lgb.early_stopping(40, verbose=False)])

    raw_va = booster.predict(Xva, num_iteration=booster.best_iteration)
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(raw_va, valid["label"])
    cal_x = np.unique(np.round(iso.X_thresholds_, 6)); cal_y = iso.predict(cal_x)
    if len(cal_x) > 400:                                           # keep the meta file small
        idx = np.linspace(0, len(cal_x) - 1, 400).astype(int); cal_x, cal_y = cal_x[idx], cal_y[idx]
    calib = lambda raw: np.interp(raw, cal_x, cal_y)               # exactly what the API does at serve time

    p_va = calib(raw_va)
    fpr, tpr, thr = roc_curve(valid["label"], p_va)
    flag_t = float(thr[np.searchsorted(fpr, 0.02, side="right") - 1])          # ~2% of honest signups challenged
    y = valid["label"].values
    block_t = 0.9
    for t in np.unique(p_va)[::-1]:                                            # lowest p with precision >= 0.9
        sel = p_va >= t
        if sel.sum() >= 50 and y[sel].mean() >= 0.9:
            block_t = float(t)
        elif sel.sum() >= 50:
            break
    block_t = max(block_t, flag_t + 0.05)

    raw_te = booster.predict(Xte, num_iteration=booster.best_iteration)
    p_te, yt = calib(raw_te), test["label"].values

    def at(t):
        sel = p_te >= t
        tp = int((sel & (yt == 1)).sum())
        return {"flagged_share": round(float(sel.mean()), 4), "precision": round(tp / max(sel.sum(), 1), 4),
                "recall": round(tp / max((yt == 1).sum(), 1), 4)}

    base = (Xte["email_disposable"].values == 1)
    metrics = {
        "split": "time-ordered 60/20/20 on synthetic data; test = latest 20% (abuser tactics drift here)",
        "n_rows": int(len(df)), "abuse_rate": round(float(df["label"].mean()), 4),
        "test_roc_auc": round(float(roc_auc_score(yt, p_te)), 4),
        "test_pr_auc": round(float(average_precision_score(yt, p_te)), 4),
        "test_recall_at_1pct_fpr": round(recall_at_fpr(yt, p_te, 0.01), 4),
        "test_at_flag_threshold": at(flag_t), "test_at_block_threshold": at(block_t),
        "baseline_disposable_list_only": {"precision": round(float(yt[base].mean()) if base.any() else 0, 4),
                                          "recall": round(float(base[yt == 1].mean()), 4)},
        "caveat": "synthetic data - measures agreement with our simulator, not real-world accuracy",
    }
    out = ROOT / "backend" / "app" / "model"
    out.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(out / "trustgate_lgb.txt"), num_iteration=booster.best_iteration)
    meta = {"features": FEATURES, "email_domain_freq": {k: v for k, v in domain_freq.items() if v >= 5e-5},
            "calibration": {"x": [float(v) for v in cal_x], "y": [float(v) for v in cal_y]},
            "thresholds": {"flag": round(flag_t, 4), "block": round(block_t, 4)}, "reason_text": REASON_TEXT,
            "trained_on": "synthetic signup data from training/generate_synthetic.py (seed 42); no real user data and "
                          "no third-party fraud dataset",
            "valid_metrics": metrics}
    (out / "model_meta.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps(metrics, indent=1)); print("flag/block thresholds:", flag_t, block_t)


if __name__ == "__main__":
    main()
