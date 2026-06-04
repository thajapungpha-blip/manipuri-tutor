"""Centralised CSS for the Manipuri Tutor app."""

import streamlit as st

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+Meetei+Mayek:wght@400;500;700&family=Noto+Serif+Bengali:wght@400;500;700&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Background */
.stApp { background: #f9fafb; }

/* Manipuri text presentation */
.manipuri-mayek {
    font-family: 'Noto Sans Meetei Mayek', 'Inter', sans-serif !important;
    font-size: 1.1rem;
    line-height: 1.95;
    color: #111827;
    white-space: pre-wrap;
}
.manipuri-beng {
    font-family: 'Noto Serif Bengali', 'Inter', sans-serif !important;
    font-size: 1.1rem;
    line-height: 1.85;
    color: #111827;
    white-space: pre-wrap;
}
.english-pane {
    font-size: 1rem;
    line-height: 1.7;
    color: #1f2937;
    white-space: pre-wrap;
}

.pane-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    color: #6b7280;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
    font-weight: 600;
}

.section-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 14px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 1rem;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}

.section-header {
    font-size: 0.85rem;
    font-weight: 700;
    color: #4b5563;
    margin-bottom: 0.6rem;
    letter-spacing: 0.02em;
}

/* Buttons — thumb-friendly */
.stButton > button, .stDownloadButton > button {
    width: 100%;
    padding: 0.7rem 1rem;
    border-radius: 10px;
    font-weight: 600;
    min-height: 46px;
    border: 1px solid #e5e7eb;
}
.stButton > button[kind="primary"] {
    background: #4f46e5;
    color: white;
    border: none;
}

/* Banners */
.trial-banner {
    background: linear-gradient(90deg, #fef3c7, #fde68a);
    color: #78350f;
    padding: 0.85rem 1.1rem;
    border-radius: 12px;
    font-weight: 600;
    margin-bottom: 1.1rem;
}
.sub-banner {
    background: linear-gradient(90deg, #dcfce7, #bbf7d0);
    color: #14532d;
    padding: 0.85rem 1.1rem;
    border-radius: 12px;
    font-weight: 600;
    margin-bottom: 1.1rem;
}
.warn-banner {
    background: linear-gradient(90deg, #fee2e2, #fecaca);
    color: #7f1d1d;
    padding: 0.85rem 1.1rem;
    border-radius: 12px;
    font-weight: 600;
    margin-bottom: 1.1rem;
}

/* Plan cards */
.plan-card {
    border: 2px solid #e5e7eb;
    border-radius: 16px;
    padding: 1.4rem 1.2rem;
    background: #ffffff;
    text-align: center;
    height: 100%;
}
.plan-card.featured {
    border-color: #4f46e5;
    box-shadow: 0 6px 18px rgba(79,70,229,0.12);
}
.plan-name {
    font-size: 0.95rem;
    font-weight: 700;
    color: #4b5563;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
.plan-price {
    font-size: 2rem;
    font-weight: 800;
    color: #111827;
    margin: 0.4rem 0 0.2rem;
}
.plan-tagline {
    font-size: 0.85rem;
    color: #6b7280;
    margin-bottom: 1rem;
}

/* Hero */
.hero-title {
    font-size: 1.7rem;
    font-weight: 800;
    color: #111827;
    margin-bottom: 0.3rem;
}
.hero-sub {
    font-size: 0.98rem;
    color: #6b7280;
    margin-bottom: 1.2rem;
}

/* Hide Streamlit menu/footer for a cleaner product feel */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }

/* Mobile tweaks */
@media (max-width: 768px) {
    .hero-title { font-size: 1.35rem; }
    .plan-price { font-size: 1.6rem; }
    .section-card { padding: 1rem; }
    .manipuri-mayek, .manipuri-beng { font-size: 1.05rem; }
}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)
