"""
Redis-backed velocity checks (sliding window counter).

Why Redis and not a SQL COUNT(*) query: velocity checks run on every single
signup/login, so they need to be O(1) and not hammer the primary database.
Redis's atomic INCR + EXPIRE gives us a cheap, accurate sliding-ish window.

If Redis isn't reachable (e.g. running backend without docker-compose for a
quick local test), we fail open to an in-memory dict so the demo never
crashes - this is a deliberate fallback, not an oversight, and is called
out in the README.
"""
import os
import time
from collections import defaultdict

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_memory_store = defaultdict(list)  # fallback: key -> list[timestamps]

try:
    import redis as redis_lib
    _client = redis_lib.from_url(REDIS_URL, socket_connect_timeout=1)
    _client.ping()
    REDIS_AVAILABLE = True
except Exception:
    _client = None
    REDIS_AVAILABLE = False


def record_and_count(key: str, window_seconds: int = 600) -> int:
    """Record one event under `key` and return how many events happened
    for that key in the last `window_seconds`. Used for both fingerprint
    velocity and IP velocity checks."""
    now = time.time()

    if REDIS_AVAILABLE:
        zkey = f"velocity:{key}"
        pipe = _client.pipeline()
        pipe.zadd(zkey, {str(now): now})
        pipe.zremrangebyscore(zkey, 0, now - window_seconds)
        pipe.zcard(zkey)
        pipe.expire(zkey, window_seconds)
        _, _, count, _ = pipe.execute()
        return int(count)

    # in-memory fallback
    _memory_store[key] = [t for t in _memory_store[key] if t > now - window_seconds]
    _memory_store[key].append(now)
    return len(_memory_store[key])


# ----------------------------------------------------------------------------------------------
# Identity history (used by the ML model)
# Mirrors exactly how training/generate_synthetic.py add_velocity() defines the features (a test checks it):
#   n_prev            = how many times this identity was seen BEFORE this event
#   secs_since_prev   = seconds since it was last seen (NaN if never)
#   same_hour/day     = events BEFORE this one inside the same clock hour / same clock day
# ----------------------------------------------------------------------------------------------
_hist_mem = {"cnt": defaultdict(int), "last": {}, "hr": defaultdict(int), "dy": defaultdict(int)}


def identity_history(key: str, now: float = None, record: bool = True) -> dict:
    now = time.time() if now is None else now
    hb, db = int(now // 3600), int(now // 86400)
    nan = float("nan")

    if REDIS_AVAILABLE:
        try:
            if record:
                pipe = _client.pipeline()
                pipe.get(f"last:{key}")
                pipe.incr(f"cnt:{key}")
                pipe.incr(f"hr:{key}:{hb}")
                pipe.expire(f"hr:{key}:{hb}", 7200)
                pipe.incr(f"dy:{key}:{db}")
                pipe.expire(f"dy:{key}:{db}", 172800)
                pipe.set(f"last:{key}", now)
                res = pipe.execute()
                last, cnt, hr, dy = res[0], int(res[1]) - 1, int(res[2]) - 1, int(res[4]) - 1
            else:   # dry run: read only, do not count this event
                last, cnt, hr, dy = _client.mget(f"last:{key}", f"cnt:{key}", f"hr:{key}:{hb}", f"dy:{key}:{db}")
                cnt, hr, dy = int(cnt or 0), int(hr or 0), int(dy or 0)
            return {"n_prev": cnt, "secs_since_prev": (now - float(last)) if last else nan,
                    "same_hour": hr, "same_day": dy}
        except Exception:
            pass  # fall through to the in-memory path rather than failing a signup

    m = _hist_mem
    last = m["last"].get(key)
    cnt, hr, dy = m["cnt"][key], m["hr"][(key, hb)], m["dy"][(key, db)]
    if record:
        m["cnt"][key] += 1; m["hr"][(key, hb)] += 1; m["dy"][(key, db)] += 1; m["last"][key] = now
    return {"n_prev": cnt, "secs_since_prev": (now - last) if last is not None else nan,
            "same_hour": hr, "same_day": dy}
