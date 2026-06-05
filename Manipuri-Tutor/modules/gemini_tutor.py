"""Gemini translator — English -> Manipuri (Bengali script).
v4: Stops hammering the API once the quota is gone (QuotaExhaustedError).
"""

import json
import time
import re

import streamlit as st
from google import genai
from google.genai import types

from modules.rate_limit import call_with_retry, QuotaExhaustedError

_MODEL_NAME = "gemini-2.5-flash"
_BATCH_SIZE = 20
_INTER_CALL_DELAY_S = 4.0

_PROSE_INSTRUCTION = """You are a precise bilingual translator for Manipuri-medium students.

Your ONLY job: translate each English sentence directly into Manipuri (Meiteilon), written in Bengali script.

Rules:
1. Translate DIRECTLY, sentence by sentence. Do NOT summarise or merge.
2. Output must contain EXACTLY the same number of items as the input, in the same order.
3. Keep technical terms, units, formulas, chemical symbols, and numbers in English.
4. If a sentence contains math, put a short spoken-form in "math_spoken" (e.g. "E equals m c squared"). Otherwise set "math_spoken" to "".
5. Write Manipuri in Bengali script ONLY. Do not use Meitei Mayek.
6. Return ONLY a JSON object:
   { "translations": [ { "id": <int>, "manipuri_beng": "...", "math_spoken": "..." }, ... ] }
"""

_POEM_INSTRUCTION = """You are a bilingual literary translator for Manipuri-medium students.

The input is POETRY. Translate each verse/line into Manipuri (Meiteilon) in Bengali script while:
1. Preserving the emotional tone and feeling of the original poem.
2. Keeping the poetic rhythm and flow — do not make it sound like plain prose.
3. Keeping the same number of output lines as input lines, in the same order.
4. Preserving rhyme where naturally possible in Manipuri.
5. Set "math_spoken" to "" always for poetry.
6. Write Manipuri in Bengali script ONLY.
7. Return ONLY a JSON object:
   { "translations": [ { "id": <int>, "manipuri_beng": "...", "math_spoken": "" }, ... ] }
"""


def detect_poem(sentences: list[str]) -> bool:
    """Heuristic: short lines + consistent short length = likely poetry."""
    if len(sentences) < 3:
        return False
    word_counts = [len(s.split()) for s in sentences]
    avg_words = sum(word_counts) / len(word_counts)
    short_ratio = sum(1 for w in word_counts if w <= 10) / len(word_counts)
    return avg_words < 9 and short_ratio > 0.70


def _repair_json(raw: str) -> str:
    raw = raw.lstrip('\ufeff').strip()
    if raw.startswith('```'):
        raw = re.sub(r'^```(?:json)?\s*', '', raw)
        raw = re.sub(r'\s*```$', '', raw)
    return raw.strip()


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        raise RuntimeError("Gemini returned an empty response.")
    for strict in (True, False):
        try:
            return json.loads(raw, strict=strict)
        except json.JSONDecodeError:
            pass
    cleaned = _repair_json(raw)
    for strict in (True, False):
        try:
            return json.loads(cleaned, strict=strict)
        except json.JSONDecodeError:
            pass
    match = re.search(r'\{.*"translations"\s*:\s*\[.*?\]\s*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(), strict=False)
        except json.JSONDecodeError:
            pass
    raise RuntimeError(f"Could not parse Gemini JSON. First 200 chars: {raw[:200]}")


def _translate_batch(batch: list[str], is_poem: bool = False) -> list[dict]:
    """One batch -> aligned list. Fresh client, used immediately (avoids the
    'client has been closed' bug). No nested retry."""
    system = _POEM_INSTRUCTION if is_poem else _PROSE_INSTRUCTION
    payload = {"sentences": [{"id": i, "english": s} for i, s in enumerate(batch)]}
    prompt = (
        ("Translate each verse/line of this poem into Manipuri (Bengali script). "
         if is_poem else
         "Translate each sentence into Manipuri (Bengali script). ")
        + "Return ONLY valid JSON. Input:\n\n"
        + json.dumps(payload, ensure_ascii=False)
    )

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=_MODEL_NAME,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3 if is_poem else 0.2,
            max_output_tokens=8192,
            response_mime_type="application/json",
        ),
    )

    data = _parse_json(response.text)
    translations = data.get("translations", [])
    if not isinstance(translations, list):
        raise RuntimeError("Gemini response missing 'translations' list.")

    by_id = {}
    for t in translations:
        if isinstance(t, dict):
            try:
                by_id[int(t.get("id"))] = t
            except (TypeError, ValueError):
                pass

    aligned = []
    for i, english in enumerate(batch):
        t = by_id.get(i, {})
        aligned.append({
            "english": english,
            "manipuri_beng": (t.get("manipuri_beng") or "").strip(),
            "math_spoken": (t.get("math_spoken") or "").strip(),
        })
    return aligned


def translate_sentences(sentences: list[str], progress_cb=None,
                        is_poem: bool = False) -> list[dict]:
    all_results = []
    total = len(sentences)
    if total == 0:
        if progress_cb:
            progress_cb(0, 0, "Nothing to translate.")
        return []

    batches = [sentences[i:i + _BATCH_SIZE] for i in range(0, total, _BATCH_SIZE)]
    done = 0
    for bi, batch in enumerate(batches):
        if progress_cb:
            progress_cb(done, total,
                        f"{'Translating poem' if is_poem else 'Translating'} "
                        f"lines {done + 1}–{done + len(batch)} of {total}…")

        def _on_wait(secs, attempt):
            if progress_cb:
                progress_cb(done, total,
                            f"Rate limit — waiting {int(secs)}s (retry {attempt})…")

        try:
            results = call_with_retry(
                lambda b=batch, p=is_poem: _translate_batch(b, p),
                on_wait=_on_wait,
            )
            all_results.extend(results)
        except QuotaExhaustedError as e:
            # Quota is gone — stop hammering. Mark this batch + all remaining
            # lines with the friendly message, then return immediately.
            msg = str(e)
            for english in batch:
                all_results.append({
                    "english": english,
                    "manipuri_beng": f"[{msg}]",
                    "math_spoken": "",
                })
            for remaining in batches[bi + 1:]:
                for english in remaining:
                    all_results.append({
                        "english": english,
                        "manipuri_beng": "[Not translated — limit reached]",
                        "math_spoken": "",
                    })
            if progress_cb:
                progress_cb(total, total, msg)
            return all_results
        except Exception as e:
            for english in batch:
                all_results.append({
                    "english": english,
                    "manipuri_beng": f"[Translation failed: {e}]",
                    "math_spoken": "",
                })

        done += len(batch)
        if bi < len(batches) - 1:
            time.sleep(_INTER_CALL_DELAY_S)

    if progress_cb:
        progress_cb(total, total, "Done.")
    return all_results


def explain_full_document(chunks, progress_cb=None):
    return translate_sentences(chunks, progress_cb=progress_cb)
