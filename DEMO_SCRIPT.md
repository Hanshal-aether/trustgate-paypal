# Demo video script (target 2:40; the rules say under 3:00, judges need not watch past 3:00)

Rules for the recording (from the official rules):
- Upload to YouTube as **Public** and test the link in a private window.
- Show the project running on your computer.
- No music unless it is royalty-free or yours. Do not show other companies' logos. PayPal's own sandbox pages are fine.
- Record in a clean browser window (new Chrome profile, hide the bookmarks bar and extra tabs).
- Never show `.env`, your Client ID or Secret, or the sandbox password on screen.
- Say it clearly: this is PayPal Sandbox, and the model is trained on synthetic data we generated.

| Time | On screen | Say |
|---|---|---|
| 0:00 | CloudNotes store | "Free trials are easy to abuse. A new email gets you another trial, and every one costs money. TrustGate stops it before the trial starts, on PayPal Subscriptions." |
| 0:20 | Honest preset, Start | "Each signup is scored first by rules and a small ML model, with reasons. This one is clean, so we go to PayPal." |
| 0:40 | PayPal Sandbox approve, return page | "The buyer approves a 7-day free trial using PayPal's Subscriptions API. It is active." |
| 1:05 | Same PayPal, new email, Start, approve with the same buyer | "Now the same person comes back with a fresh email. Nothing looks wrong before PayPal." |
| 1:30 | Return page: Trial cancelled | "After approval TrustGate reads the subscription, sees this PayPal account already has a trial, and cancels the new one through the API." |
| 1:50 | Free-trial farm preset, Start 2-3 times | "Throwaway emails from a datacenter are blocked before PayPal is called." |
| 2:10 | Console: Trials, then Model | "Every decision has reasons and a PayPal subscription id. The model is trained on synthetic data we generated, and the page says so." |
| 2:30 | Terminal: pytest, then GitHub page | "22 tests, open source, setup instructions in the README. Next: an AI agent that resolves account-sharing cases without ever blocking a payment." |

The separate 2-minute walkaround (for advisors and clients, not for Devpost): problem 20s, the PayPal-account catch 60s,
"payments are never blocked, only sharing is resolved" 20s, what you want from the viewer 20s.
