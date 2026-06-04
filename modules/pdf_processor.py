"""PDF text extraction — produces a clean list of SENTENCES for direct
line-by-line translation (not chunked paragraphs).

We do three passes:
1. Pull raw text out of each PDF page with pypdf.
2. Fix typical PDF line-wrap artifacts:
     - hyphenated word breaks  ("informa-\\ntion" -> "information")
     - mid-paragraph single newlines  -> space
     - double newlines preserved as paragraph breaks
3. Split paragraphs into sentences on ". ! ?" followed by whitespace.

Each returned item is one sentence string — small enough to translate
directly without summarising.
"""

from io import BytesIO
import re

from pypdf import PdfReader

# Sentences shorter than this are treated as fragments and joined with the
# next sentence (avoids one-word "sections" like "Fig. 2.1").
_MIN_SENTENCE_CHARS = 8


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    reader = PdfReader(BytesIO(pdf_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text)
    return "\n\n".join(pages)


def _clean_pdf_text(raw: str) -> str:
    # Join hyphenated words split across lines: "informa-\ntion" -> "information"
    txt = re.sub(r"-\s*\n\s*", "", raw)
    # Collapse runs of 3+ newlines to exactly 2 (paragraph break)
    txt = re.sub(r"\n{3,}", "\n\n", txt)
    # Within a paragraph (single newlines), join lines with a space
    paragraphs = txt.split("\n\n")
    fixed_paragraphs = []
    for p in paragraphs:
        p = re.sub(r"[ \t]*\n[ \t]*", " ", p)
        p = re.sub(r"[ \t]+", " ", p).strip()
        if p:
            fixed_paragraphs.append(p)
    return "\n\n".join(fixed_paragraphs)


# Split on sentence-ending punctuation followed by whitespace + capital/digit.
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def _split_paragraph_to_sentences(paragraph: str) -> list[str]:
    parts = _SENTENCE_SPLIT.split(paragraph)
    # Merge tiny fragments forward (e.g. "Fig. 2.1" wrongly split)
    merged: list[str] = []
    for s in parts:
        s = s.strip()
        if not s:
            continue
        if merged and len(merged[-1]) < _MIN_SENTENCE_CHARS:
            merged[-1] = merged[-1] + " " + s
        else:
            merged.append(s)
    return merged


def extract_sentences(pdf_bytes: bytes) -> list[str]:
    """Return a list of sentences extracted from the PDF, in reading order."""
    raw = extract_text_from_pdf(pdf_bytes)
    if not raw.strip():
        return []
    cleaned = _clean_pdf_text(raw)
    sentences: list[str] = []
    for paragraph in cleaned.split("\n\n"):
        sentences.extend(_split_paragraph_to_sentences(paragraph))
    return sentences


# --- Kept for backward compatibility (older code paths) -----------------
def extract_pdf_chunks(pdf_bytes: bytes) -> list[str]:
    """Legacy paragraph-chunk extractor. Prefer extract_sentences()."""
    return extract_sentences(pdf_bytes)
