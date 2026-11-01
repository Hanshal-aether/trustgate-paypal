# TrustGate for PayPal: stop free-trial abuse before the trial starts

A demo store (**CloudNotes**) sells a 7-day free trial through **PayPal Subscriptions**. **TrustGate** sits in front of PayPal:

1. **Before PayPal is called**, every signup gets a risk score (0-100) and a decision: allow, flag (one-time code) or block.
   Rules (disposable email, datacenter IP, device and IP velocity) and a small ML model are combined; the higher score wins,
   and every decision lists its reasons. A blocked signup never reaches PayPal.
2. **After the buyer approves on PayPal**, TrustGate reads the subscription. If that **PayPal account already holds another
   free trial**, TrustGate cancels the new one through the PayPal API. Changing email or device does not help the abuser.
3. A console shows signups, trials (with PayPal subscription ids), households and the model.

Anti-account-sharing ("household trust") is included as a second module: unknown devices get a one-time code and earn trust over time.

## Run it (Windows, Mac or Linux with Docker Desktop)

1. **PayPal Sandbox keys** (free, ~10 min): developer.paypal.com, log in, **Apps & Credentials**, switch to **Sandbox**,
   **Create App** (name it `trustgate`), copy the **Client ID** and **Secret**. Under **Testing tools > Sandbox accounts** open the
   **Personal** account: its email and password are your test buyer.
2. In this folder, copy `.env.example` to `.env` (PowerShell: `copy .env.example .env`) and paste the Client ID and Secret.
3. `docker compose up --build` (first build takes a few minutes).
4. Open `http://localhost:8000/api/paypal/status`. You should see `"configured": true`.
5. Open **http://localhost:4173/#/cloudnotes** and try the three stories:
   - **Honest customer:** Start, then **Continue to PayPal**, log in as the Sandbox buyer, approve. You return to "free trial is active".
   - **Same PayPal, new email:** Start, approve with the SAME buyer. You return to **Trial cancelled**; TrustGate cancelled it via the API.
   - **Free-trial farm:** press Start two or three times. It escalates to **BLOCK**; PayPal is never called.
   Then open the console (`http://localhost:4173/#/app`) and look at **Trials** and **Model**.

**Sandbox tip (important):** create your Sandbox **Business and Personal accounts with country United States**. Accounts created
with country India made PayPal's approval page fail with "We're sorry, things don't appear to be working" in our testing.
Create the app (type Merchant) with the US Business account, and log in on the PayPal page with the US Personal buyer.

Troubleshooting: "PayPal is not set up" means `.env` was not picked up (`docker compose up -d --force-recreate backend`).
"PayPal sign-in failed" means wrong keys or Live keys instead of Sandbox. Switching PayPal apps: `curl -X POST http://localhost:8000/api/paypal/reset`.

## For judges: quick start (about 10 minutes)

Needs Docker Desktop and a free PayPal developer account. No real money is involved.
1. Create Sandbox keys as in step 1 above (US accounts), put them in `.env`, run `docker compose up --build`.
2. Open `http://localhost:4173/#/cloudnotes` and run the three stories in step 5. Story 2 needs the SAME Sandbox buyer as Story 1.
3. Open `http://localhost:4173/#/app/trials` to see every decision, reason and PayPal subscription id.
4. Run the tests: `docker compose exec backend pytest -q`.

## What was built during the Submission Period (Oct 1 - Nov 12, 2026)

Everything PayPal-related is new for this hackathon: the Subscriptions integration (product, trial plan, subscription, cancel,
webhook verification), the TrustGate check in front of PayPal, payer-account reuse detection with API cancellation, the CloudNotes
store, the Trials console page, the synthetic-data signup model and its training pipeline, the CC0 disposable-email list integration,
and the tests. The generic signup-scoring and household-trust modules were started earlier as part of the same TrustGate idea and were
substantially reworked here.

## Tests

`docker compose exec backend pytest -q` runs 22 backend tests. The PayPal tests use a fake PayPal server, so they never touch the
network: they cover the plan shape (7-day free TRIAL then paid REGULAR cycle), block-never-calls-PayPal, challenge flow,
payer-reuse cancellation, idempotent confirm and webhook handling. Live Sandbox behaviour is what steps 4-5 above exercise.

## How the AI part works, and what it is not

The ML model is LightGBM trained on **synthetic signup data we generate ourselves** (`training/generate_synthetic.py`), plus the
CC0 disposable-email list. Metrics on that data show the pipeline works; they are **not** real-world accuracy.
Read `MODEL_CARD.md`. Retrain with `python training/train.py`. If the model files are missing, the rules keep working alone.

## Architecture

FastAPI + SQLAlchemy (Postgres) + Redis (sliding-window velocity counters) + React/Vite console. PayPal calls: OAuth2,
`/v1/catalogs/products`, `/v1/billing/plans`, `/v1/billing/subscriptions` (create, get, cancel), webhook verification.
IDs: UUIDv4 for security tokens (device, OTP), time-ordered UUIDv7 for event logs.

## Limits (honest list)

Sandbox only. Demo OTP is shown on screen instead of emailed. IP reputation is a small local heuristic, not a paid API.
No authentication or multi-tenancy yet. The model is trained on synthetic data. Raw emails and IPs are stored, so real use needs a
retention policy and privacy review.

## AI assistance disclosure

This project was built with the help of Claude (Anthropic) as a coding and design assistant, directed and reviewed by the author.

## License and credits

AGPL-3.0 (see `LICENSE`). Third-party data and libraries: `NOTICE.md`. Disposable-email list: CC0 1.0.
