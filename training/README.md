Retrain the model (about 30 seconds, CPU only):

    pip install lightgbm scikit-learn pandas numpy
    python training/train.py

It regenerates the synthetic data (seed 42), trains, calibrates, and overwrites `backend/app/model/trustgate_lgb.txt`
and `model_meta.json`. Restart the backend afterwards. Then copy the new numbers into `frontend/src/benchmarks.js`.
