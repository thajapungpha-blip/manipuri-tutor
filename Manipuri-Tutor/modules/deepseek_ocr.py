"""OCR via DeepSeek Vision (OpenAI-compatible API).

Same interface as modules/ocr.py — `extract_sentences_from_image`,
`mime_for_filename`, `IMAGE_EXTENSIONS` — so app.py only needs its import
line swapped from `modules.ocr` to `modules.deepseek_ocr`.

IMPORTANT: set _VISION_MODEL below to the image-capable model your DeepSeek
API account actually exposes (check platform.deepseek.com). If the model
does not accept images, you'll get a clear, friendly error so you know to
switch models or use a different OCR.
"""

import json
import base64
import hashlib

import streamlit as st
from openai import OpenAI

from modules.rate_limit import call_with_retry  # QuotaExhaustedError propagates

# <<< SET THIS to your DeepSeek vision/OCR model name from the API dashboard >>>
_VISION_MODEL = "deepseek-chat"
_BASE_URL = "https://api.deepseek.com"

# Shared, bounded in-process cache so the same page is never re-sent.
_OCR_CACHE: dict[str, list[str]] = {}
_OCR_CACHE_MAX = 200

_OCR_SYSTEM = """You are an OCR assistant for Class 11 English textbook photographs.

Your task: read a photograph of a textbook page and extract its readable English text in natural reading order.

Strict rules:
1. Extract main body text, section headings, captions, table entries, and figure labels — all are educational content the student needs.
2. SKIP page numbers, running headers (chapter name printed at the very top of every page), and watermarks.
3. Output text EXACTLY as printed. Do NOT summarise, paraphrase, correct, or translate.
4. Preserve numbers, units, formulas, scientific notation, and original English punctuation.
5. If part of the page is blurry, glare-affected, or unreadable, skip that part. Do NOT guess or invent text.
6. Each sentence or short standalone item (heading, caption, table row) is one array element.
7. Return ONLY a JSON object of this exact shape, with no extra text:
   { "sentences": ["...", "...", ...] }
"""


def _client() -> OpenAI:
    return OpenAI(api_key=st.secrets["DEEPSEEK_API_KEY"], base_url=_BASE_URL)


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
        # last resort: grab the first {...} block
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start:end + 1]
        return json.loads(cleaned)


def extract_sentences_from_image(
    image_bytes: bytes,
    mime_type: str,
    on_wait=None,
) -> list[str]:
    """OCR one image via DeepSeek vision; return sentences in reading order.

    Cached by image content hash. Raises a clear error if the chosen model
    cannot accept image input through the API.
    """
    key = hashlib.sha256(image_bytes).hexdigest()
    cached = _OCR_CACHE.get(key)
    if cached is not None:
        return list(cached)

    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime_type};base64,{b64}"
    client = _client()

    def _call():
        return client.chat.completions.create(
            model=_VISION_MODEL,
            messages=[
                {"role": "system", "content": _OCR_SYSTEM},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Extract the readable English text from this "
                                "textbook page photo. Return ONLY the JSON object "
                                "specified in your instructions."
                            ),
                        },
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=8192,
        )

    try:
        response = call_with_retry(_call, on_wait=on_wait)
    except Exception as e:
        emsg = str(e).lower()
        if ("image" in emsg or "vision" in emsg or "multimodal" in emsg
                or "content" in emsg and "type" in emsg):
            raise RuntimeError(
                "This DeepSeek model can't read images through the API. "
                "Set _VISION_MODEL to a vision-capable model, or use a "
                "different OCR (Gemini / Bhashini / Tesseract)."
            ) from e
        raise

    raw = response.choices[0].message.content if response.choices else ""
    data = _parse_json(raw)
    sentences = [s.strip() for s in data.get("sentences", [])
                 if isinstance(s, str) and s.strip()]

    if sentences:
        if len(_OCR_CACHE) >= _OCR_CACHE_MAX:
            _OCR_CACHE.clear()
        _OCR_CACHE[key] = list(sentences)
    return sentences


_IMAGE_MIME = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "heic": "image/heic",
    "heif": "image/heif",
}


def mime_for_filename(name: str) -> str:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    return _IMAGE_MIME.get(ext, "image/jpeg")


IMAGE_EXTENSIONS = tuple(_IMAGE_MIME.keys())
