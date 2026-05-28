"""Firestore CRUD for the users collection."""

from datetime import datetime, timezone, timedelta
from firebase_admin import firestore


def _db():
    return firestore.client()


def get_or_create_user(uid: str, email: str) -> dict:
    """Fetch user doc, creating it with defaults on first sign-in."""
    ref = _db().collection("users").document(uid)
    snap = ref.get()
    if snap.exists:
        return snap.to_dict()
    user = {
        "email": email,
        "trial_files_processed": 0,
        "subscription_status": "inactive",
        "subscription_expiry": None,
        "stripe_customer_id": None,
        "created_at": datetime.now(timezone.utc),
    }
    ref.set(user)
    return user


def refresh_user(uid: str) -> dict | None:
    snap = _db().collection("users").document(uid).get()
    return snap.to_dict() if snap.exists else None


def increment_trial(uid: str) -> dict:
    ref = _db().collection("users").document(uid)
    ref.update({"trial_files_processed": firestore.Increment(1)})
    return refresh_user(uid)


def activate_subscription(uid: str, duration_days: int, stripe_customer_id: str | None = None) -> dict:
    expiry = datetime.now(timezone.utc) + timedelta(days=duration_days)
    updates = {
        "subscription_status": "active",
        "subscription_expiry": expiry,
    }
    if stripe_customer_id:
        updates["stripe_customer_id"] = stripe_customer_id
    _db().collection("users").document(uid).update(updates)
    return refresh_user(uid)


def cancel_subscription(uid: str) -> dict:
    _db().collection("users").document(uid).update({"subscription_status": "cancelled"})
    return refresh_user(uid)


def set_last_checkout_session(uid: str, session_id: str) -> None:
    """Remember the most recent Stripe Checkout Session for this user so the
    'Sync Subscription' button can look it up later."""
    _db().collection("users").document(uid).update(
        {"last_stripe_session_id": session_id}
    )


def is_subscription_active(user_data: dict | None) -> bool:
    if not user_data:
        return False
    if user_data.get("subscription_status") != "active":
        return False
    expiry = user_data.get("subscription_expiry")
    if expiry is None:
        return False
    if hasattr(expiry, "tzinfo") and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    return expiry > datetime.now(timezone.utc)


def trial_remaining(user_data: dict | None, limit: int) -> int:
    if not user_data:
        return limit
    used = user_data.get("trial_files_processed", 0)
    return max(0, limit - used)
