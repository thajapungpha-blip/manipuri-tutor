"""Rate-limit retry helper for Gemini API calls.

Gemini's free tier allows ~10 requests/minute on Flash. When we burst a
PDF/photo set through it, we predictably hit a 429 "ResourceExhausted"
error. The error message tells us exactly how long to wait, e.g.:

    429 You exceeded your current quota ... Please retry in 52.77s.

This module wraps any callable, catches 429-shaped errors, parses the
suggested retry delay, sleeps, and retries up to MAX_RETRIES times.
A small inter-call delay can also be added to stay under the per-minute
limit pre-emptively.
"""

import re
import time

MAX_RETRIES = 4          # total attempts (1 initial + 3 retries)
HARD_WAIT_CAP_S = 65.0   # never sleep longer than this between retries
FALLBACK_BASE_S = 8.0    # used if we cannot parse the retry hint

_RETRY_HINT = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)


def _looks_like_rate_limit(msg: str) -> bool:
    msg_low = msg.lower()
    return (
        "429" in msg
        or "rate limit" in msg_low
        or "quota" in msg_low
        or "resourceexhausted" in msg_low.replace(" ", "")
        or "resource exhausted" in msg_low
    )


def _suggested_wait(msg: str, attempt: int) -> float:
    """Pick a sleep duration from the error message, or back off exponentially."""
    m = _RETRY_HINT.search(msg)
    if m:
        # +1s safety buffer so we are firmly past the window edge
        return min(float(m.group(1)) + 1.0, HARD_WAIT_CAP_S)
    return min(FALLBACK_BASE_S * (2 ** attempt), HARD_WAIT_CAP_S)


def call_with_retry(fn, *, on_wait=None):
    """Call `fn()`; on 429-style errors sleep and retry. Re-raise on final fail.

    `on_wait(seconds, attempt)` (optional) is invoked just before each sleep
    so the UI can surface "waiting N seconds" to the user.
    """
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 — SDK can raise many error classes
            last_err = e
            if not _looks_like_rate_limit(str(e)):
                raise
            if attempt == MAX_RETRIES - 1:
                break
            wait_s = _suggested_wait(str(e), attempt)
            if on_wait:
                try:
                    on_wait(wait_s, attempt + 1)
                except Exception:
                    pass
            time.sleep(wait_s)
    # Exhausted retries
    raise last_err  # type: ignore[misc]
