"""Centralised CSS for Manipuri Tutor — polished, modern, student-friendly."""

import streamlit as st


def inject_css():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&family=Noto+Sans+Bengali:wght@400;500;600&display=swap');

        /* ---------- Global ---------- */
        .stApp {
            background: linear-gradient(160deg, #f5f7fa 0%, #eef2f7 40%, #e8edf5 100%);
        }
        html, body, [class*="css"] {
            font-family: 'Poppins', sans-serif;
        }

        /* ---------- Hero header ---------- */
        .hero-title {
            font-size: 2.4rem;
            font-weight: 800;
            background: linear-gradient(90deg, #6d28d9 0%, #db2777 60%, #f59e0b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.2rem;
            letter-spacing: -0.5px;
        }
        .hero-sub {
            font-size: 1.02rem;
            color: #475569;
            font-weight: 400;
            margin-bottom: 0.8rem;
            line-height: 1.5;
        }

        /* ---------- Banners ---------- */
        .sub-banner, .trial-banner, .warn-banner {
            padding: 0.85rem 1.2rem;
            border-radius: 14px;
            font-weight: 600;
            font-size: 1rem;
            margin: 0.6rem 0 1.2rem 0;
            box-shadow: 0 4px 14px rgba(0,0,0,0.06);
        }
        .sub-banner {
            background: linear-gradient(90deg, #d1fae5 0%, #a7f3d0 100%);
            color: #065f46;
            border: 1px solid #6ee7b7;
        }
        .trial-banner {
            background: linear-gradient(90deg, #fef3c7 0%, #fde68a 100%);
            color: #92400e;
            border: 1px solid #fcd34d;
        }
        .warn-banner {
            background: linear-gradient(90deg, #fee2e2 0%, #fecaca 100%);
            color: #991b1b;
            border: 1px solid #fca5a5;
        }

        /* ---------- Section / line cards ---------- */
        .section-card {
            background: #ffffff;
            border-radius: 18px;
            padding: 1.3rem 1.5rem;
            margin-bottom: 1.1rem;
            box-shadow: 0 6px 20px rgba(15, 23, 42, 0.06);
            border: 1px solid #eef0f4;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }
        .section-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 28px rgba(15, 23, 42, 0.10);
        }
        .section-header {
            display: inline-block;
            font-weight: 700;
            font-size: 0.8rem;
            color: #6d28d9;
            background: #f3e8ff;
            padding: 0.25rem 0.8rem;
            border-radius: 999px;
            margin-bottom: 0.9rem;
            letter-spacing: 0.3px;
        }
        .pane-label {
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 1px;
            color: #94a3b8;
            text-transform: uppercase;
            margin-bottom: 0.4rem;
        }
        .english-pane {
            font-size: 1.08rem;
            color: #1e293b;
            line-height: 1.65;
            font-weight: 400;
        }
        .manipuri-beng {
            font-family: 'Noto Sans Bengali', sans-serif;
            font-size: 1.28rem;
            color: #0f172a;
            line-height: 1.85;
            font-weight: 500;
        }
        .manipuri-mayek {
            font-size: 1.5rem;
            color: #0f172a;
            line-height: 1.9;
            font-weight: 500;
        }

        /* ---------- Buttons ---------- */
        .stButton > button {
            border-radius: 12px !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
            border: none !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(90deg, #6d28d9 0%, #db2777 100%) !important;
            color: white !important;
            box-shadow: 0 4px 14px rgba(109, 40, 217, 0.3) !important;
        }
        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(109, 40, 217, 0.4) !important;
        }

        /* ---------- File uploader ---------- */
        [data-testid="stFileUploader"] {
            background: #ffffff;
            border-radius: 16px;
            padding: 1rem;
            border: 2px dashed #c4b5fd;
        }

        /* ---------- Plan cards ---------- */
        .plan-card {
            background: #ffffff;
            border-radius: 18px;
            padding: 1.8rem 1.4rem;
            text-align: center;
            box-shadow: 0 6px 20px rgba(15,23,42,0.06);
            border: 1px solid #eef0f4;
            margin-bottom: 0.8rem;
        }
        .plan-card.featured {
            border: 2px solid #db2777;
            box-shadow: 0 10px 28px rgba(219, 39, 119, 0.18);
        }
        .plan-name { font-weight: 700; font-size: 1.2rem; color: #1e293b; }
        .plan-price { font-weight: 800; font-size: 2.2rem;
            background: linear-gradient(90deg, #6d28d9, #db2777);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            margin: 0.4rem 0; }
        .plan-tagline { color: #64748b; font-size: 0.92rem; }

        /* ---------- Sidebar ---------- */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #ffffff 0%, #faf5ff 100%);
        }

        /* ---------- Audio player ---------- */
        audio { width: 100%; margin-top: 0.5rem; border-radius: 10px; }

        /* ---------- Hide Streamlit chrome ---------- */
        #MainMenu { visibility: hidden; }
        footer { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )
