"""
Manipuri Tutor — main Streamlit application.
v3: Clear button + poem detection (cropper removed).
"""

import html

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

import streamlit as st

from modules.auth import (
    initialize_firebase,
    sign_in_user,
    sign_up_user,
    send_password_reset,
)
from modules.firestore_db import (
    get_or_create_user,
    refresh_user,
    increment_trial,
    activate_subscription,
    is_subscription_active,
    trial_remaining,
    set_last_checkout_session,
)
from modules.pdf_processor import extract_sentences
from modules.deepseek_ocr import (
    extract_sentences_from_image,
    mime_for_filename,
    IMAGE_EXTENSIONS,
)
try:
    from modules.deepseek_tutor import translate_sentences, detect_poem
except ImportError:
    from modules.deepseek_tutor import translate_sentences
    def detect_poem(sentences):
        return False
from modules.transliterate import bengali_to_meitei_mayek
from modules.bhashini_tts import synthesize_speech
from modules.stripe_payments import (
    create_checkout_session,
    verify_payment,
    load_subscription_config,
    get_billing_portal_url,
)
from modules.styles import inject_css

# ---------------------------------------------------------------------------
# App config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Manipuri Tutor",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="auto",
)
inject_css()

try:
    initialize_firebase()
except Exception as e:
    st.error(f"❌ Firebase failed to initialize: {e}")
    st.stop()

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------
_DEFAULTS = {
    "uid": None,
    "email": None,
    "id_token": None,
    "user_data": None,
    "page": "main",
    "auth_mode": "login",
    "sections": None,
    "is_poem": False,
    "script_choice": "Meitei Mayek",
    "voice_choice": "Female",
    "uploaded_filename": None,
    "_payment_checked": False,
}
for _k, _v in _DEFAULTS.items():
    st.session_state.setdefault(_k, _v)


def _app_base_url() -> str:
    return st.secrets.get("APP_BASE_URL", "http://localhost:8501")


def _handle_stripe_return():
    if st.session_state._payment_checked:
        return
    qp = st.query_params
    if "session_id" not in qp:
        return
    if not st.session_state.uid:
        return
    sid = qp["session_id"]
    st.session_state._payment_checked = True
    try:
        result = verify_payment(sid)
        if result["paid"] and result["uid"] == st.session_state.uid:
            st.session_state.user_data = activate_subscription(
                st.session_state.uid,
                result["duration_days"],
                stripe_customer_id=result.get("customer_id"),
            )
            st.success("✅ Payment confirmed — your subscription is active!")
            st.session_state.page = "main"
        elif result["paid"]:
            st.warning("Payment confirmed but UID mismatch. Contact support.")
        else:
            st.warning("Payment not yet completed.")
            st.session_state.page = "paywall"
    except Exception as e:
        st.error(f"Could not verify payment: {e}")
    finally:
        try:
            st.query_params.clear()
        except Exception:
            pass


_handle_stripe_return()


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
def render_sidebar():
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        st.session_state.script_choice = st.radio(
            "Script",
            ["Meitei Mayek", "Bengali Script"],
            index=0 if st.session_state.script_choice == "Meitei Mayek" else 1,
            key="sb_script_radio",
        )
        st.session_state.voice_choice = st.radio(
            "Voice",
            ["Female", "Male"],
            index=0 if st.session_state.voice_choice == "Female" else 1,
            key="sb_voice_radio",
        )
        st.markdown("---")
        st.markdown("### 💳 Subscription")
        if st.button("🔄 Sync subscription", key="sb_sync_sub",
                     use_container_width=True):
            _sync_subscription_from_stripe()


def _sync_subscription_from_stripe():
    user = refresh_user(st.session_state.uid) or {}
    sid = user.get("last_stripe_session_id")
    if not sid:
        st.sidebar.warning("No recent checkout to sync.")
        return
    try:
        result = verify_payment(sid)
        if result["paid"]:
            st.session_state.user_data = activate_subscription(
                st.session_state.uid,
                result["duration_days"],
                stripe_customer_id=result.get("customer_id"),
            )
            st.sidebar.success("✅ Subscription is active.")
        else:
            st.sidebar.info("Payment not yet completed.")
    except Exception as e:
        st.sidebar.error(f"Sync failed: {e}")


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
def render_header():
    left, right = st.columns([3, 2])
    with left:
        st.markdown(
            '<div class="hero-title">📚 Manipuri Tutor</div>'
            '<div class="hero-sub">English textbook-ki line khudingmakki Manipuri-da '
            'direct translation — Meitei Mayek script-ga audio-ga.</div>',
            unsafe_allow_html=True,
        )
    with right:
        if st.session_state.uid:
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🏠 Home", key="nav_home"):
                    st.session_state.page = "main"
                    st.rerun()
            with c2:
                if st.button("👤 Account", key="nav_account"):
                    st.session_state.page = "account"
                    st.rerun()
            with c3:
                if st.button("🚪 Logout", key="nav_logout"):
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.rerun()


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def render_auth():
    render_header()
    st.markdown("&nbsp;")
    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        tab_login, tab_signup = st.tabs(["Sign in", "Create account"])

        with tab_login:
            with st.form("login_form", clear_on_submit=False):
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_pw")
                submitted = st.form_submit_button("Sign in", type="primary",
                                                  use_container_width=True)
                if submitted:
                    if not email or not password:
                        st.error("Enter both email and password.")
                    else:
                        try:
                            with st.spinner("Signing in…"):
                                resp = sign_in_user(email.strip(), password)
                                _post_auth(resp)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))

            with st.expander("Forgot password?"):
                rst_email = st.text_input("Account email", key="reset_email")
                if st.button("Send reset link", key="reset_btn"):
                    try:
                        send_password_reset(rst_email.strip())
                        st.success("Reset link sent. Check your inbox.")
                    except Exception as e:
                        st.error(str(e))

        with tab_signup:
            with st.form("signup_form", clear_on_submit=False):
                email = st.text_input("Email", key="signup_email")
                password = st.text_input(
                    "Password (min 6 characters)",
                    type="password",
                    key="signup_pw",
                )
                submitted = st.form_submit_button(
                    "Create account", type="primary", use_container_width=True
                )
                if submitted:
                    if not email or not password:
                        st.error("Enter both email and password.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters.")
                    else:
                        try:
                            with st.spinner("Creating your account…"):
                                resp = sign_up_user(email.strip(), password)
                                _post_auth(resp)
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))


def _post_auth(resp: dict):
    uid = resp["localId"]
    email = resp["email"]
    st.session_state.uid = uid
    st.session_state.email = email
    st.session_state.id_token = resp.get("idToken")
    st.session_state.user_data = get_or_create_user(uid, email)


# ---------------------------------------------------------------------------
# Clear helper
# ---------------------------------------------------------------------------
def _clear_translation():
    st.session_state.sections = None
    st.session_state.uploaded_filename = None
    st.session_state.is_poem = False
    # Clear all audio cache
    for k in list(st.session_state.keys()):
        if k.startswith("audio_") or k.startswith("full_audio"):
            del st.session_state[k]


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
def render_main():
    render_header()

    # Status banner — FREE FOR ALL
    st.markdown(
        '<div class="sub-banner">🎁 Free for all students — no subscription needed!</div>',
        unsafe_allow_html=True,
    )

    # Clear button — only show when translation exists
    if st.session_state.sections:
        if st.button("🗑️ New Translation", key="btn_clear", type="secondary"):
            _clear_translation()
            st.rerun()

    can_process = True

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------
    uploaded_files = st.file_uploader(
        "Upload a PDF or photos of textbook pages",
        type=["pdf", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        disabled=not can_process,
        key="pdf_uploader",
        help=(
            "Upload a textbook PDF, or take phone photos of pages. "
            "For photos, upload one page at a time for best results."
        ),
    )

    upload_id = None
    if uploaded_files:
        upload_id = "|".join(f"{f.name}:{f.size}" for f in uploaded_files)

    # ------------------------------------------------------------------
    # New upload detected
    # ------------------------------------------------------------------
    if uploaded_files and upload_id != st.session_state.uploaded_filename:
        st.session_state.uploaded_filename = upload_id
        st.session_state.sections = None
        st.session_state.is_poem = False

        pdf_files = [f for f in uploaded_files if f.name.lower().endswith(".pdf")]
        image_files = [f for f in uploaded_files
                       if f.name.lower().endswith(IMAGE_EXTENSIONS)]

        sentences: list[str] = []

        if pdf_files:
            if len(uploaded_files) > 1:
                st.info("PDF detected — only the first PDF is used.")
            with st.spinner("Reading PDF…"):
                try:
                    sentences = extract_sentences(pdf_files[0].read())
                except Exception as e:
                    st.error(f"Could not read PDF: {e}")
                    return

        elif image_files:
            progress = st.progress(0.0, text="Reading photos…")
            for idx, img in enumerate(image_files):
                progress.progress(
                    idx / max(len(image_files), 1),
                    text=f"Reading photo {idx + 1} of {len(image_files)}: {img.name}",
                )

                def _ocr_wait(secs, attempt, _idx=idx, _img=img):
                    try:
                        progress.progress(
                            _idx / max(len(image_files), 1),
                            text=f"Rate limit — waiting {int(secs)}s…",
                        )
                    except Exception:
                        pass

                try:
                    extracted = extract_sentences_from_image(
                        img.read(),
                        mime_for_filename(img.name),
                        on_wait=_ocr_wait,
                    )
                    sentences.extend(extracted)
                except Exception as e:
                    st.warning(f"Skipped {img.name}: {e}")
            progress.empty()

        if not sentences:
            st.error(
                "Could not extract any text. For PDFs, check the file is not "
                "scan-only. For photos, make sure the page is in focus and well-lit."
            )
            return

        # Detect poem
        is_poem = detect_poem(sentences)
        st.session_state.is_poem = is_poem

        progress = st.progress(0.0, text="Starting translation…")

        def _cb(done, total, msg):
            try:
                progress.progress(min(1.0, done / max(total, 1)), text=msg)
            except Exception:
                pass

        try:
            sections = translate_sentences(sentences, progress_cb=_cb, is_poem=is_poem)
        except Exception as e:
            st.error(f"Gemini failed: {e}")
            return

        for s in sections:
            s["manipuri_mayek"] = bengali_to_meitei_mayek(s.get("manipuri_beng", ""))

        st.session_state.sections = sections

        progress.empty()
        poem_note = " 🎵 Poem detected — translated poetically." if is_poem else ""
        st.success(f"Translated {len(sections)} line{'s' if len(sections) != 1 else ''}.{poem_note}")
        st.rerun()

    # ------------------------------------------------------------------
    # Render results
    # ------------------------------------------------------------------
    if st.session_state.sections:
        sections = st.session_state.sections
        voice = st.session_state.voice_choice
        is_poem = st.session_state.get("is_poem", False)

        # Clear button (top of results)
        col_title, col_btn = st.columns([4, 1])
        with col_title:
            if is_poem:
                st.markdown("### 🎵 Poem Translation")
                st.caption("Poetry detected — translation preserves verse structure and feeling.")
            else:
                st.markdown("### 🔊 Full Audio")
        with col_btn:
            if st.button("🗑️ Clear", key="btn_clear2", type="secondary"):
                _clear_translation()
                st.rerun()

        # Full audio
        full_audio_key = f"full_audio_{voice.lower()}"
        if st.button(f"▶️ Play Full Translation ({voice})", key="btn_full_audio",
                     use_container_width=False, type="primary"):
            with st.spinner("Generating full audio — please wait…"):
                try:
                    full_text = " ".join(
                        s.get("manipuri_beng", "") for s in sections
                        if s.get("manipuri_beng", "")
                    )
                    audio_bytes = synthesize_speech(full_text, voice.lower())
                    st.session_state[full_audio_key] = audio_bytes
                except Exception:
                    st.info(
                        "🎧 **Audio coming soon** — Bhashini TTS integration pending approval."
                    )
                    st.session_state[full_audio_key] = None

        if st.session_state.get(full_audio_key):
            st.audio(st.session_state[full_audio_key], format="audio/wav")

        st.markdown("### Line-by-line translation")
        for i, sec in enumerate(sections):
            _render_section(i, sec, is_poem=is_poem)


def _render_section(i: int, sec: dict, is_poem: bool = False):
    with st.container():
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        label = f"{'Verse' if is_poem else 'Line'} {i + 1}"
        st.markdown(f'<div class="section-header">{label}</div>', unsafe_allow_html=True)

        col_en, col_mn = st.columns(2)
        with col_en:
            st.markdown('<div class="pane-label">English</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="english-pane">{html.escape(sec["english"])}</div>',
                unsafe_allow_html=True,
            )
        with col_mn:
            if st.session_state.script_choice == "Meitei Mayek":
                label_mn = "Manipuri · Meitei Mayek"
                css_class = "manipuri-mayek"
                text = sec.get("manipuri_mayek") or ""
            else:
                label_mn = "Manipuri · Bengali Script"
                css_class = "manipuri-beng"
                text = sec.get("manipuri_beng") or ""
            st.markdown(f'<div class="pane-label">{label_mn}</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="{css_class}">{html.escape(text)}</div>',
                unsafe_allow_html=True,
            )

        voice = st.session_state.voice_choice
        audio_key = f"audio_sec{i}_{voice.lower()}"
        btn_key = f"btn_audio_{i}_{voice.lower()}"

        ac1, ac2 = st.columns([1, 4])
        with ac1:
            play = st.button(f"🔊 Play ({voice})", key=btn_key, use_container_width=True)
        if play:
            with st.spinner("Generating audio…"):
                try:
                    text_for_tts = sec.get("manipuri_beng", "")
                    if sec.get("math_spoken"):
                        text_for_tts = (text_for_tts + " " + sec["math_spoken"]).strip()
                    audio_bytes = synthesize_speech(text_for_tts, voice.lower())
                    st.session_state[audio_key] = audio_bytes
                except Exception:
                    st.info("🎧 Audio coming soon — Bhashini TTS pending approval.")
                    st.session_state[audio_key] = None

        if st.session_state.get(audio_key):
            st.audio(st.session_state[audio_key], format="audio/wav")

        st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Paywall
# ---------------------------------------------------------------------------
def render_paywall():
    render_header()
    cfg = load_subscription_config()
    plans = cfg["plans"]
    st.markdown("## Choose a plan")
    cols = st.columns(len(plans))
    for col, (plan_key, plan) in zip(cols, plans.items()):
        featured = plan.get("featured", False)
        with col:
            st.markdown(
                f'<div class="plan-card {"featured" if featured else ""}">'
                f'<div class="plan-name">{html.escape(plan["name"])}</div>'
                f'<div class="plan-price">₹{plan["price_inr"]}</div>'
                f'<div class="plan-tagline">{html.escape(plan["tagline"])}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"Subscribe — ₹{plan['price_inr']}", key=f"plan_btn_{plan_key}",
                         type="primary" if featured else "secondary",
                         use_container_width=True):
                try:
                    base = _app_base_url()
                    checkout_url, sid = create_checkout_session(
                        uid=st.session_state.uid,
                        email=st.session_state.email,
                        plan_key=plan_key,
                        success_url=base,
                        cancel_url=base,
                    )
                    try:
                        set_last_checkout_session(st.session_state.uid, sid)
                    except Exception:
                        pass
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={checkout_url}">',
                                unsafe_allow_html=True)
                    st.markdown(f"[Tap here to pay]({checkout_url})")
                except Exception as e:
                    st.error(f"Could not start checkout: {e}")


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------
def render_account():
    render_header()
    st.markdown("## Your account")
    user = refresh_user(st.session_state.uid) or {}
    st.session_state.user_data = user
    st.markdown(f"**Email:** {st.session_state.email}")

    if is_subscription_active(user):
        expiry = user.get("subscription_expiry")
        st.markdown(
            '<div class="sub-banner">Subscription: <b>Active</b> — '
            f'expires {expiry.strftime("%d %b %Y") if expiry else "N/A"}'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="trial-banner">Subscription: <b>Inactive</b></div>',
                    unsafe_allow_html=True)
        if st.button("Subscribe →", type="primary", key="account_subscribe"):
            st.session_state.page = "paywall"
            st.rerun()

    cfg = load_subscription_config()
    st.markdown(f"**Free trial used:** {user.get('trial_files_processed', 0)} / {cfg['free_trial_limit']}")
    st.markdown("---")
    ac1, ac2 = st.columns(2)
    with ac1:
        if st.button("🔄 Sync subscription", key="account_sync_sub", use_container_width=True):
            _sync_subscription_from_stripe()
            st.rerun()
    with ac2:
        cust = user.get("stripe_customer_id")
        if cust:
            if st.button("Manage billing", key="open_portal", use_container_width=True):
                try:
                    url = get_billing_portal_url(cust, _app_base_url())
                    st.markdown(f'<meta http-equiv="refresh" content="0;url={url}">',
                                unsafe_allow_html=True)
                    st.markdown(f"[Open billing portal]({url})")
                except Exception as e:
                    st.error(f"Could not open billing portal: {e}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
def main():
    if not st.session_state.uid:
        render_auth()
        return
    render_sidebar()
    page = st.session_state.page
    if page == "paywall":
        render_paywall()
    elif page == "account":
        render_account()
    else:
        render_main()


if __name__ == "__main__":
    main()
