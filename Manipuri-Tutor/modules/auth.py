"""
Firebase authentication helpers.

`firebase-admin` does NOT support email/password sign-in directly (it's a
server-side admin tool). For sign-in/sign-up we hit Firebase Auth REST API.
For user management, token verification and Firestore we use firebase-admin.
"""

import json
import requests
import streamlit as st
import firebase_admin
from firebase_admin import credentials

FIREBASE_AUTH_BASE = "https://identitytoolkit.googleapis.com/v1/accounts"


def initialize_firebase():
    """Idempotent initialization of the firebase-admin SDK from Streamlit secrets."""
    if firebase_admin._apps:
        return
    sa_raw = st.secrets["FIREBASE_SERVICE_ACCOUNT"]
    # secrets can deliver this as a TOML table (dict-like) or a JSON string
    if isinstance(sa_raw, str):
        sa_dict = json.loads(sa_raw)
    else:
        sa_dict = dict(sa_raw)
    # Streamlit's TOML parser can mangle the private_key newlines — normalize
    if "private_key" in sa_dict and "\\n" in sa_dict["private_key"]:
        sa_dict["private_key"] = sa_dict["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(sa_dict)
    firebase_admin.initialize_app(cred)


def _web_api_key() -> str:
    return st.secrets["FIREBASE_WEB_API_KEY"]


def sign_in_user(email: str, password: str) -> dict:
    """Sign in an existing user. Returns dict with localId (uid), email, idToken."""
    url = f"{FIREBASE_AUTH_BASE}:signInWithPassword?key={_web_api_key()}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code == 200:
        return r.json()
    raise RuntimeError(_friendly_error(r.json()))


def sign_up_user(email: str, password: str) -> dict:
    """Create a new user. Returns dict with localId (uid), email, idToken."""
    url = f"{FIREBASE_AUTH_BASE}:signUp?key={_web_api_key()}"
    payload = {"email": email, "password": password, "returnSecureToken": True}
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code == 200:
        return r.json()
    raise RuntimeError(_friendly_error(r.json()))


def send_password_reset(email: str) -> None:
    url = f"{FIREBASE_AUTH_BASE}:sendOobCode?key={_web_api_key()}"
    payload = {"requestType": "PASSWORD_RESET", "email": email}
    r = requests.post(url, json=payload, timeout=15)
    if r.status_code != 200:
        raise RuntimeError(_friendly_error(r.json()))


def _friendly_error(resp_json: dict) -> str:
    code = resp_json.get("error", {}).get("message", "UNKNOWN_ERROR")
    head = code.split(":")[0].strip() if ":" in code else code
    mapping = {
        "EMAIL_NOT_FOUND": "No account exists with that email.",
        "INVALID_PASSWORD": "Incorrect password.",
        "INVALID_LOGIN_CREDENTIALS": "Invalid email or password.",
        "INVALID_EMAIL": "That doesn't look like a valid email address.",
        "EMAIL_EXISTS": "An account with this email already exists.",
        "WEAK_PASSWORD": "Password must be at least 6 characters.",
        "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts — please wait a moment and try again.",
        "USER_DISABLED": "This account has been disabled.",
        "OPERATION_NOT_ALLOWED": "Email/password sign-in is not enabled in your Firebase project.",
    }
    return mapping.get(head, f"Authentication error: {code}")
