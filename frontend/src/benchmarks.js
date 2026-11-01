// Numbers shown on the Landing and Model pages. They come from backend/app/model/model_meta.json, written by
// `python training/train.py`. They are measured on SYNTHETIC data we generate ourselves (training/generate_synthetic.py),
// so they show that the pipeline works, not how well it would do on real customers.
export const EVAL = {
  "rocAuc": 0.9569,
  "prAuc": 0.8582,
  "recallAt1Fpr": 0.7358,
  "flag": {
    "flagged_share": 0.0855,
    "precision": 0.7617,
    "recall": 0.7865
  },
  "block": {
    "flagged_share": 0.0683,
    "precision": 0.8824,
    "recall": 0.7286
  },
  "baseline": {
    "precision": 0.6201,
    "recall": 0.3129
  },
  "rows": 150000,
  "abuseRate": 0.08
}
