# Submission checklist (based on the official rules)

**Deadline: 12 Nov 2026, 12:00 pm Pacific = about 1:30 AM IST on 13 Nov (Pacific time moves to standard time on 1 Nov).
Your own target: submit by 5 Nov, which leaves a week of safety.** Judging 1-15 Dec, winners about 21 Dec. Prize paperwork
and payment come after that (the rules allow up to 60 days after the forms), so do not plan on prize money before 2027.

## Must-haves (the rules)
- [ ] Project uses PayPal (Sandbox) and an AI model/tool, and runs as shown in the video
- [ ] Text description of features and functionality (draft below)
- [ ] Public repo on GitHub with an open-source license **visible in the About box at the top of the repo page**
      (after pushing, the sidebar must say "AGPL-3.0 license". If it says "View license" or nothing, delete `LICENSE` on GitHub and
      use **Add file > Create new file > name it LICENSE > Choose a license template**)
- [ ] Repo contains all source, assets and run instructions (README "For judges" section)
- [ ] Video under 3 minutes, public on YouTube, shows the project running, no copyrighted music, no other brands' logos
- [ ] Explain how the project was significantly updated during the Submission Period (in the README and the Devpost text)
- [ ] All materials in English

## Safety
- [ ] `git status` before committing: no `.env`, no `*.db`
- [ ] After pushing, open the repo in a private window and confirm `.env` is not there
- [ ] Optional: put dedicated judge Sandbox keys and a buyer login ONLY in Devpost's testing-instructions field, never in GitHub;
      delete that PayPal app after 15 Dec

## Your own items
- [ ] All 3 stories worked live (done) and screenshots saved
- [ ] You are 18 or older, and the person who submits is the Representative of the team
- [ ] Submitted, not left as Draft, and the confirmation email arrived

## Devpost text draft

**Inspiration.** Free trials are the easiest thing on a subscription product to abuse, and every abused trial costs real money.

**What it does.** TrustGate scores each signup before PayPal is called (rules plus a small ML model, with plain-language reasons).
Clean signups go to a PayPal Subscription with a 7-day free trial. Risky ones get a one-time code or are blocked, and PayPal is never
called. After approval it checks whether that PayPal account already holds another trial and cancels the new one through the API.
A console shows signups, trials and the model. Paying customers are never blocked from paying.

**How we built it.** FastAPI, PostgreSQL, Redis, React, Docker. PayPal Subscriptions API on Sandbox: catalog products, billing plans
(TRIAL then REGULAR cycle), subscriptions (create, get, cancel), webhook signature verification. AI: a LightGBM model with calibrated
scores and per-decision reasons, trained on synthetic signup data we generate ourselves, combined with a rule engine and a CC0
disposable-email list.

**Built during the Submission Period.** The PayPal integration, payer-reuse detection and cancellation, the CloudNotes store, the
Trials console, the synthetic-data model and its training pipeline, and the tests are new for this hackathon. The generic signup-scoring
and household-trust modules were started earlier as part of the same idea and substantially reworked here.

**Challenges.** Keeping honest customers out of the way (a flag means a one-time code, not a ban), and being honest about the model:
it is trained on synthetic data, so we report its numbers as a pipeline check, not real-world accuracy. Also: Sandbox accounts created
with country India failed on PayPal's approval page, so we use US accounts.

**What's next.** An AI agent that resolves account-sharing cases (offer a family plan or a verification step instead of blocking a paying
customer), real labelled data from a live store, and multi-tenant API keys.

**Built with.** Python, FastAPI, PostgreSQL, Redis, LightGBM, React, Docker, PayPal Subscriptions API.
**AI assistance:** built with Claude as a coding assistant, directed and reviewed by the author.
