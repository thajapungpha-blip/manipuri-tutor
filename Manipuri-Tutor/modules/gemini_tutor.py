"""Gemini translator — DIRECT line-by-line English -> Manipuri (Bengali script).

Earlier version of this module asked Gemini to *explain / summarise* whole
paragraphs. Student feedback (collected May 2026) preferred a direct
sentence-by-sentence translation so they can match each English line to its
Manipuri equivalent. This module implements that.

We batch ~20 sentences per Gemini call and require the model to return a JSON
array with the same number of items, in the same order.
"""

import json
import time

import streamlit as st
from google import genai
from google.genai import types

from modules.rate_limit import call_with_retry

_MODEL_NAME = "gemini-2.5-flash"

_BATCH_SIZE = 40
_INTER_CALL_DELAY_S = 4.0

SYSTEM_INSTRUCTION = """You are a precise bilingual translator for Manipuri-medium Class 11 students.

Your ONLY job: translate each English sentence directly into Manipuri (Meiteilon), written in Bengali script (Assamese/Bengali Unicode block).

Strict rules:
1. Translate DIRECTLY, sentence by sentence. Do NOT summarise. Do NOT explain. Do NOT merge sentences.
2. Output must contain EXACTLY the same number of items as the input, in the same order.
3. Keep all technical terms, units, formulas, equations, chemical symbols, and numbers in English / their original form. Do not transliterate them.
4. If a sentence contains a mathematical expression, also produce a short spoken-form of just that expression in the "math_spoken" field (e.g. "E equals m c squared"). If there is no math, set "math_spoken" to "".
5. Write Manipuri in Bengali script ONLY. Do not use Meitei Mayek.
6. Preserve the meaning and tone of the original. Do not add commentary.
7. Return ONLY a JSON object of this exact shape:
   { "translations": [ { "id": <int>, "manipuri_beng": "...", "math_spoken": "..." }, ... ] }
   Where "id" matches the input id for that sentence.
"""


def _get_client():
    api_key = st.secrets["GEMINI_API_KEY"]
    return genai.Client(api_key=api_key)


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError("Gemini returned an empty response.")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip("` \n")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)


def _translate_batch(batch: list[str]) -> list[dict]:
    """Translate one batch. Returns aligned list of dicts of same length as batch."""
    client = _get_client()
    payload = {
        "sentences": [{"id": i, "english": s} for i, s in enumerate(batch)]
    }
    prompt = (
        "Translate each sentence below directly into Manipuri (Bengali script). "
        "Return JSON exactly as your instructions specify. Input:\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )
    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_INSTRUCTION,
            temperature=0.2,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )
    data = _parse_json(response.text)
    translations = data.get("translations", [])
    if not isinstance(translations, list):
        raise RuntimeError("Gemini response did not contain 'translations' list.")

    by_id: dict[int, dict] = {}
    for t in translations:
        if not isinstance(t, dict):
            continue
        try:
            tid = int(t.get("id"))
        except (TypeError, ValueError):
            continue
        by_id[tid] = t

    aligned: list[dict] = []
    for i, english in enumerate(batch):
        t = by_id.get(i, {})
        aligned.append({
            "english": english,
            "manipuri_beng": (t.get("manipuri_beng") or "").strip(),
            "math_spoken": (t.get("math_spoken") or "").strip(),
        })
    return aligned


def translate_sentences(sentences: list[str], progress_cb=None) -> list[dict]:
    all_sections: list[dict] = []
    total = len(sentences)
    if total == 0:
        if progress_cb:
            progress_cb(0, 0, "Nothing to translate.")
        return []

    batches: list[list[str]] = [
        sentences[i:i + _BATCH_SIZE]
        for i in range(0, total, _BATCH_SIZE)
    ]
    done = 0
    for bi, batch in enumerate(batches):
        if progress_cb:
            progress_cb(done, total,
                        f"Translating sentences {done + 1}–{done + len(batch)} of {total}…")

        def _on_wait(secs: float, attempt: int):
            if progress_cb:
                progress_cb(
                    done, total,
                    f"Rate limit reached — waiting {int(secs)}s "
                    f"(retry {attempt}) before continuing…",
                )

        try:
            secs = call_with_retry(lambda: _translate_batch(batch),
                                   on_wait=_on_wait)
            all_sections.extend(secs)
        except Exception as e:
            for english in batch:
                all_sections.append({
                    "english": english,
                    "manipuri_beng": f"[Translation failed: {e}]",
                    "math_spoken": "",
                })
        done += len(batch)
        if bi < len(batches) - 1:
            time.sleep(_INTER_CALL_DELAY_S)

    if progress_cb:
        progress_cb(total, total, "Done.")
    return all_sections


# --- Backward-compatible alias ---------------------------------------------
def explain_full_document(chunks: list[str], progress_cb=None) -> list[dict]:
    """Legacy entry point. Now performs direct sentence translation."""
    return translate_sentences(chunks, progress_cb=progress_cb)
