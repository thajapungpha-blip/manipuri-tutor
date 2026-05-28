"""OCR via Gemini 2.5 Flash Vision.

Students photograph textbook pages with their phones and upload them.
This module runs each photo through Gemini Vision to extract the body
text as a clean list of sentences — same format as `pdf_processor.extract_sentences`,
so the downstream translate pipeline does not need to change.
"""

import json
import streamlit as st
from google import genai
from google.genai import types

from modules.rate_limit import call_with_retry

_MODEL_NAME = "gemini-2.5-flash"

_OCR_SYSTEM = """You are an OCR assistant for Class 11 English textbook photographs.

Your task: read a photograph of a textbook page and extract its readable English text in natural reading order.

Strict rules:
1. Extract main body text, section headings, captions, table entries, and figure labels — all are educational content the student needs.
2. SKIP page numbers, running headers (chapter name printed at the very top of every page), and watermarks.
3. Output text EXACTLY as printed. Do NOT summarise, paraphrase, correct, or translate.
4. Preserve numbers, units, formulas, scientific notation, and original English punctuation.
5. If part of the page is blurry, glare-affected, or unreadable, skip that part. Do NOT guess or invent text.
6. Each sentence or short standalone item (heading, caption, table row) is one array element.
7. Return ONLY a JSON object of this exact shape:
   { "sentences": ["...", "...", ...] }
"""


def _get_client():
    api_key = st.secrets["GEMINI_API_KEY"]
    return genai.Client(api_key=api_key)


def _parse_json(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        cleaned = raw.strip("` \n")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()
        return json.loads(cleaned)


def extract_sentences_from_image(
    image_bytes: bytes,
    mime_type: str,
    on_wait=None,
) -> list[str]:
    """OCR one image; return list of sentences in reading order."""
    client = _get_client()

    def _call():
        return client.models.generate_content(
            model=_MODEL_NAME,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                "Extract the readable English text from this textbook page photo. "
                "Return JSON exactly as your instructions specify.",
            ],
            config=types.GenerateContentConfig(
                system_instruction=_OCR_SYSTEM,
                temperature=0.1,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
        )

    response = call_with_retry(_call, on_wait=on_wait)
    data = _parse_json(response.text)
    sentences = data.get("sentences", [])
    return [s.strip() for s in sentences if isinstance(s, str) and s.strip()]


_IMAGE_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
}


def mime_for_filename(name: str) -> str:
    """Return a Gemini-acceptable MIME string for an image filename."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return _IMAGE_MIME.get(ext, "image/jpeg")


IMAGE_EXTENSIONS = tuple(_IMAGE_MIME.keys())
