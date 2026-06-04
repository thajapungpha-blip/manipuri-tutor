"""Stripe Checkout integration — no-webhook flow.

Streamlit Community Cloud cannot reliably host webhook endpoints, so we use
the pragmatic pattern recommended in the spec:

  1. Create a Checkout Session; redirect the user to Stripe.
  2. On success, Stripe redirects back to our app with `?session_id=...`.
  3. On load, the app reads `session_id` from the query params and calls
     `verify_payment` which polls the Stripe API directly to confirm.
  4. If `payment_status == 'paid'`, we activate the subscription in Firestore.
"""

import json
from pathlib import Path

import stripe
import streamlit as st

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "subscription.json"


def _init_stripe():
    stripe.api_key = st.secrets["STRIPE_SECRET_KEY"]


def load_subscription_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def create_checkout_session(uid: str, email: str, plan_key: str,
                            success_url: str, cancel_url: str) -> tuple[str, str]:
    """Create a Stripe Checkout Session for the chosen plan.

    Returns (checkout_url, session_id).
    """
    _init_stripe()
    cfg = load_subscription_config()
    plan = cfg["plans"].get(plan_key)
    if plan is None:
        raise ValueError(f"Unknown plan: {plan_key}")

    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
        success_url=(
            f"{success_url}?session_id={{CHECKOUT_SESSION_ID}}&plan={plan_key}"
        ),
        cancel_url=cancel_url,
        client_reference_id=uid,
        customer_email=email,
        metadata={
            "uid": uid,
            "plan": plan_key,
            "duration_days": str(plan["duration_days"]),
        },
        subscription_data={
            "metadata": {
                "uid": uid,
                "plan": plan_key,
                "duration_days": str(plan["duration_days"]),
            }
        },
    )
    return session.url, session.id


def verify_payment(session_id: str) -> dict:
    """Poll Stripe for the status of a Checkout Session."""
    _init_stripe()
    session = stripe.checkout.Session.retrieve(session_id)
    paid = session.payment_status == "paid"
    duration = int(session.metadata.get("duration_days", 0) or 0)
    return {
        "paid": paid,
        "uid": session.metadata.get("uid") or session.client_reference_id,
        "plan": session.metadata.get("plan"),
        "duration_days": duration,
        "customer_id": session.customer,
    }


def get_billing_portal_url(customer_id: str, return_url: str) -> str:
    _init_stripe()
    portal = stripe.billing_portal.Session.create(
        customer=customer_id, return_url=return_url
    )
    return portal.url
