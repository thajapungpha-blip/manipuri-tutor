"""
Bhashini ULCA pipeline for Manipuri TTS.

Two-step flow:
 1. POST to config endpoint to obtain the callback URL, inferenceApiKey and
    serviceId for the requested task + source language.
 2. POST to that callback URL with the actual TTS task to get base64 WAV.

Audio is cached locally by SHA-256(text + gender). Streamlit Cloud's
filesystem is ephemeral across deploys but persists across reruns within a
session, which still avoids repeated API calls during a user's session.
"""

import base64
import hashlib
from pathlib import Path

import requests
import streamlit as st

BHASHINI_CONFIG_URL = (
    "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
)

CACHE_DIR = Path("tts_cache")
CACHE_DIR.mkdir(exist_ok=True)


def _hash_key(text: str, gender: str) -> str:
    return hashlib.sha256(f"{gender.lower()}::{text}".encode("utf-8")).hexdigest()


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.wav"


def synthesize_speech(text: str, gender: str = "female") -> bytes | None:
    """Return WAV bytes for the given Manipuri (Bengali-script) text."""
    if not text or not text.strip():
        return None

    gender = (gender or "female").lower()
    if gender not in ("female", "male"):
        gender = "female"

    key = _hash_key(text, gender)
    cached = _cache_path(key)
    if cached.exists():
        return cached.read_bytes()

    user_id = st.secrets["BHASHINI_USER_ID"]
    api_key = st.secrets["BHASHINI_API_KEY"]
    # Default pipeline ID = MeitY's public pipeline; override via secret if needed
    pipeline_id = st.secrets.get("BHASHINI_PIPELINE_ID", "64392f96daac500b55c543cd")

    # --- Step 1: config -----------------------------------------------------
    cfg_headers = {
        "userID": user_id,
        "ulcaApiKey": api_key,
        "Content-Type": "application/json",
    }
    cfg_payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {"language": {"sourceLanguage": "mni"}},
            }
        ],
        "pipelineRequestConfig": {"pipelineId": pipeline_id},
    }
    cfg_resp = requests.post(
        BHASHINI_CONFIG_URL, headers=cfg_headers, json=cfg_payload, timeout=30
    )
    if cfg_resp.status_code != 200:
        raise RuntimeError(
            f"Bhashini config failed ({cfg_resp.status_code}): {cfg_resp.text[:300]}"
        )
    cfg_json = cfg_resp.json()

    pipeline_resp_cfg = cfg_json.get("pipelineResponseConfig") or []
    if not pipeline_resp_cfg or not pipeline_resp_cfg[0].get("config"):
        raise RuntimeError(
            "Bhashini does not currently expose a TTS service for Manipuri (mni) "
            "on this pipeline. Try a different BHASHINI_PIPELINE_ID."
        )
    service_id = pipeline_resp_cfg[0]["config"][0]["serviceId"]

    endpoint_info = cfg_json["pipelineInferenceAPIEndPoint"]
    callback_url = endpoint_info["callbackUrl"]
    auth = endpoint_info["inferenceApiKey"]

    # --- Step 2: inference --------------------------------------------------
    infer_headers = {
        auth["name"]: auth["value"],
        "Content-Type": "application/json",
    }
    infer_payload = {
        "pipelineTasks": [
            {
                "taskType": "tts",
                "config": {
                    "language": {"sourceLanguage": "mni"},
                    "serviceId": service_id,
                    "gender": gender,
                },
            }
        ],
        "inputData": {"input": [{"source": text}]},
    }
    infer_resp = requests.post(
        callback_url, headers=infer_headers, json=infer_payload, timeout=60
    )
    if infer_resp.status_code != 200:
        raise RuntimeError(
            f"Bhashini inference failed ({infer_resp.status_code}): "
            f"{infer_resp.text[:300]}"
        )
    infer_json = infer_resp.json()

    try:
        audio_b64 = infer_json["pipelineResponse"][0]["audio"][0]["audioContent"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected Bhashini response shape: {e}") from e

    audio_bytes = base64.b64decode(audio_b64)
    cached.write_bytes(audio_bytes)
    return audio_bytes
