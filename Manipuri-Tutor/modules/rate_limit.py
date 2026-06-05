"""Rate-limit retry helper for Gemini API calls.

Two kinds of 429 are handled very differently:

  * Per-minute throttle (recoverable) -> short retry, then continue.
  * Daily-quota / long cooldown (waiting won't help in a web session)
    -> raise QuotaExhaustedError immediately so the UI shows a clean
       "limit reached, try later" message instead of hanging.

The total time spent waiting inside a single call is HARD-CAPPED, so a
student never sits through minutes of "waiting 59s..." before a failure.

`call_with_retry(fn, on_wait=...)` keeps the same signature as before,
so existing callers (ocr.py, gemini_tutor.py) work unchanged.
"""

import re
import time
import random


class QuotaExhaustedError(RuntimeError):
    """Raised when the Gemini quota is exhausted and waiting won't help soon.

    The message is already student-friendly and safe to show in the UI.
    """


MAX_RETRIES = 3              # short throttles only
PER_RETRY_CAP_S = 20.0       # never sleep more than this in one go
TOTAL_WAIT_BUDGET_S = 35.0   # never spend more than this waiting, total
FALLBACK_BASE_S = 5.0        # used if we cannot parse the retry hint

_RETRY_HINT = re.compile(r"retry in (\d+(?:\.\d+)?)\s*s", re.IGNORECASE)

_FRIENDLY_MINUTE = (
    "Free usage limit was hit for a moment. Please wait a minute and try again."
)
_FRIENDLY_DAILY = (
    "Today's free usage limit has been reached. Please try again later."
)


def _is_rate_limit(msg: str) -> bool:
    m = msg.lower()
    return (
        "429" in msg
        or "rate limit" in m
        or "quota" in m
        or "resourceexhausted" in m.replace(" ", "")
        or "resource exhausted" in m
    )


def _is_daily(msg: str) -> bool:
    """Free-tier daily caps name 'PerDay' in the quota metric; long cooldowns
    and 'daily' wording also mean: don't make the student wait."""
    m = msg.lower().replace(" ", "")
    return (
        "perday" in m
        or "requestsperday" in m
        or "daily" in m
        or "freetier" in m
    )


def _hint_seconds(msg: str):
    mt = _RETRY_HINT.search(msg)
    return float(mt.group(1)) if mt else None


def call_with_retry(fn, *, on_wait=None):
    """Call `fn()`; on a short 429 throttle, sleep briefly and retry.

    On a daily quota / long cooldown, raise QuotaExhaustedError right away.
    `on_wait(seconds, attempt)` (optional) is called before each sleep so the
    UI can show "waiting N seconds".
    """
    spent = 0.0
    for attempt in range(MAX_RETRIES):
        try:
            return fn()
        except QuotaExhaustedError:
            raise
        except Exception as e:  # noqa: BLE001 - SDK raises many error classes
            msg = str(e)
            if not _is_rate_limit(msg):
                raise  # genuine bug — let it surface normally

            # Daily cap or long cooldown: waiting is pointless this session.
            if _is_daily(msg):
                raise QuotaExhaustedError(_FRIENDLY_DAILY) from e

            hint = _hint_seconds(msg)
            if hint is not None and hint > PER_RETRY_CAP_S:
                # API wants a long wait -> treat like a daily/long cooldown.
                raise QuotaExhaustedError(_FRIENDLY_DAILY) from e

            if attempt == MAX_RETRIES - 1:
                raise QuotaExhaustedError(_FRIENDLY_MINUTE) from e

            base = hint if hint is not None else FALLBACK_BASE_S * (attempt + 1)
            wait_s = min(base + random.uniform(0.3, 1.2), PER_RETRY_CAP_S)
            if spent + wait_s > TOTAL_WAIT_BUDGET_S:
                raise QuotaExhaustedError(_FRIENDLY_MINUTE) from e

            if on_wait:
                try:
                    on_wait(wait_s, attempt + 1)
                except Exception:
                    pass
            time.sleep(wait_s)
            spent += wait_s

    raise QuotaExhaustedError(_FRIENDLY_MINUTE)
