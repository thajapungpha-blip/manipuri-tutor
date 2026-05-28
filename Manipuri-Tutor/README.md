# Manipuri Tutor 📚

An AI-powered web app that turns English textbook PDFs into **direct line-by-line Manipuri (Meiteilon) translation** in Meitei Mayek script (with a Bengali-script toggle) and a built-in audio lecture mode.

Built for Manipuri-medium Class 11 students. Runs in any modern browser. Free to start, with a pay-per-week / month / year subscription model.

> **Quickstart on Windows:** double-click `RUN.bat`. Streamlit boots and your browser opens automatically at <http://localhost:8501>.

---

## What it does

1. Student logs in (Firebase Auth).
2. Uploads an English textbook PDF.
3. Gemini reads the PDF and translates each English sentence directly into Bengali-script Manipuri (math/units kept in English). No summarising — students can match each English line to its Manipuri equivalent.
4. The app transliterates that to Meitei Mayek instantly — the student toggles between the two scripts.
5. "🔊 Play" sends the Manipuri text to Bhashini TTS (Female/Male) and plays a WAV in the browser.
6. First file is free. After that, Stripe Checkout unlocks unlimited access.

---

## Local setup

### 1. Clone & install

```bash
git clone <your-repo>
cd manipuri-tutor
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure secrets

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml — fill in real values (see below)
```

### 3. Run

```bash
streamlit run app.py
```

Open <http://localhost:8501>.

---

## Getting the credentials

### Firebase

1. Go to <https://console.firebase.google.com>, create a project.
2. **Authentication → Sign-in method → Email/Password → Enable.**
3. **Firestore Database → Create database** (Production mode, region nearest to you).
4. **Project settings → Service accounts → Generate new private key.** This downloads a JSON file. Paste its contents into `FIREBASE_SERVICE_ACCOUNT` (keep the surrounding `"""..."""` triple quotes).
5. **Project settings → General → Your apps → Web app.** Copy the `apiKey` value into `FIREBASE_WEB_API_KEY`.
6. **Firestore → Rules** — paste:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{uid} {
      // Only the admin SDK (server) writes to this collection. The client
      // never reads/writes directly.
      allow read, write: if false;
    }
  }
}
```

### Gemini

1. <https://aistudio.google.com/apikey> → **Create API key**.
2. Paste into `GEMINI_API_KEY`.

### Bhashini ULCA

1. Register at <https://bhashini.gov.in/ulca/>.
2. **Profile → API Key**. Note your `userID` and `ulcaApiKey`.
3. Put them in `BHASHINI_USER_ID` and `BHASHINI_API_KEY`.
4. The default pipeline ID (`64392f96daac500b55c543cd`) is MeitY's public pipeline; override with `BHASHINI_PIPELINE_ID` if you want a different one.

> **Note on Manipuri TTS availability.** Bhashini's TTS coverage for `mni` (Manipuri) can change. If you see "Bhashini does not currently expose a TTS service for Manipuri" at runtime, switch to a pipeline ID that includes it, or temporarily disable audio.

### Stripe

1. Create an account at <https://dashboard.stripe.com>.
2. **Products → Add product** — create three recurring prices (weekly, monthly, yearly) in INR. For each, copy the **Price ID** (`price_...`).
3. **Developers → API keys** — copy your secret + publishable keys.
4. Put the secret into `STRIPE_SECRET_KEY`, publishable into `STRIPE_PUBLISHABLE_KEY`.
5. Open `config/subscription.json` and replace the three `price_REPLACE_*` strings with your real Stripe Price IDs.

---

## Deploy to Streamlit Community Cloud

1. Push the repo to GitHub (make sure `.streamlit/secrets.toml` is **not** committed — it's in `.gitignore`).
2. Go to <https://share.streamlit.io>, click **New app**, pick the repo, set `app.py` as the entry point.
3. **Advanced → Secrets** — paste the contents of your `secrets.toml`.
4. After the first deploy, copy the public URL (e.g. `https://manipuri-tutor.streamlit.app`) and put it back into the secret `APP_BASE_URL`. Re-deploy. (This is how Stripe knows where to redirect users after payment.)

That's it — share the URL with students.

---

## Admin: changing prices and trial limit

Open `config/subscription.json`:

```json
{
  "free_trial_limit": 1,
  "plans": {
    "weekly":  { "price_inr": 29,  "duration_days": 7,   "stripe_price_id": "price_...", ... },
    "monthly": { "price_inr": 99,  "duration_days": 30,  "stripe_price_id": "price_...", ... },
    "yearly":  { "price_inr": 499, "duration_days": 365, "stripe_price_id": "price_...", ... }
  }
}
```

- **Change the displayed price** → edit `price_inr` *and* update the corresponding price in Stripe (or create a new Stripe price and paste its ID into `stripe_price_id`).
- **Change duration** → edit `duration_days` (this controls Firestore expiry; Stripe handles its own renewals).
- **Change trial allowance** → edit `free_trial_limit` (1 = first file free, 0 = no trial).

Commit and redeploy — no code changes needed.

---

## Architecture notes

- `app.py` — Streamlit UI, routing (auth / main / paywall / account), session state.
- `modules/auth.py` — Firebase Auth REST API for sign-in/sign-up; `firebase-admin` init for Firestore.
- `modules/firestore_db.py` — User documents (`users/{uid}`) including `last_stripe_session_id`.
- `modules/pdf_processor.py` — PyMuPDF extraction + ~1000-word chunking.
- `modules/gemini_tutor.py` — Gemini 1.5 Flash with `response_mime_type: "application/json"` so the model is constrained to return the exact schema.
- `modules/transliterate.py` — `indic-transliteration` (Bengali → MEETEI_MAYEK) primary, with `aksharamukha` and a manual map as defensive fallbacks.
- `modules/bhashini_tts.py` — Two-step ULCA pipeline (config → inference) + SHA-256 disk cache.
- `modules/stripe_payments.py` — Checkout session creation + `verify_payment()` polling. **No webhooks** — Streamlit Cloud doesn't host them reliably, so we verify when the user is redirected back with `?session_id=...` or via the **Sync subscription** button.
- `modules/styles.py` — CSS injection: Noto Sans Meetei Mayek, Noto Serif Bengali, thumb-friendly buttons, mobile breakpoints.

---

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| "Failed to initialize Firebase" | The service account JSON in secrets has unescaped newlines. Use the example template — keep `\\n` inside `private_key`. |
| Login works locally but fails on Cloud | Check that **APP_BASE_URL** matches the deployed URL exactly (no trailing slash). |
| "Bhashini does not currently expose a TTS service for Manipuri" | Try a different `BHASHINI_PIPELINE_ID`, or check that your ULCA account is approved for TTS. |
| Stripe redirect lands on a 404 | Make sure `APP_BASE_URL` is set in secrets. |
| Meitei Mayek shows as boxes | The Google Font is loading but the device's font cache needs a refresh — force-reload the page. |
| Sub-active but still asked to pay | Tap **🏠 Home** in the header — it refreshes the user document from Firestore. |

---

## License

Source supplied for use by Akashvani Imphal / All India Radio internal teams. Adapt freely.
