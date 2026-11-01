"""Disposable-email domain list.

Source: github.com/disposable-email-domains/disposable-email-domains (CC0 1.0 public-domain dedication; see
app/data/disposable_email_blocklist.LICENSE.txt). If the file is missing we fall back to a tiny built-in set so
the service still starts.
"""
from pathlib import Path

_FALLBACK = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "yopmail.com",
             "trashmail.com", "throwawaymail.com", "fakeinbox.com", "getnada.com", "maildrop.cc"}


def _load() -> frozenset:
    path = Path(__file__).parent / "data" / "disposable_email_blocklist.conf"
    try:
        domains = {ln.strip().lower() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")}
        return frozenset(domains) if domains else frozenset(_FALLBACK)
    except OSError:
        return frozenset(_FALLBACK)


DISPOSABLE_DOMAINS = _load()


def is_disposable(email: str) -> bool:
    domain = email.split("@")[-1].lower().strip()
    return domain in DISPOSABLE_DOMAINS
