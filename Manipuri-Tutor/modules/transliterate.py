"""
Bengali (Bangla) script → Meitei Mayek transliteration.

Primary engine:  `indic-transliteration` (sanscript), `BENGALI → MEETEI_MAYEK`.
Fallback 1:      `aksharamukha` — robust for conjuncts.
Fallback 2:      character-by-character map below (lossy on conjuncts, used
                 only if both libraries fail at runtime).
"""

try:
    from indic_transliteration import sanscript as _sanscript
    from indic_transliteration.sanscript import transliterate as _indic_translit
    _HAS_INDIC = True
except Exception:
    _HAS_INDIC = False

try:
    from aksharamukha import transliterate as _aksh
    _HAS_AKSH = True
except Exception:
    _HAS_AKSH = False


def bengali_to_meitei_mayek(text: str) -> str:
    if not text:
        return ""

    # 1. Try indic-transliteration first (matches spec)
    if _HAS_INDIC:
        try:
            return _indic_translit(text, _sanscript.BENGALI, _sanscript.MEETEI_MAYEK)
        except Exception:
            pass  # fall through

    # 2. Fall back to aksharamukha
    if _HAS_AKSH:
        try:
            return _aksh.process("Bengali", "MeeteiMayek", text)
        except Exception:
            pass

    # 3. Last-resort manual character map
    return _manual_translit(text)


# --- Fallback map (Bengali Unicode block -> Meetei Mayek Unicode block) -----
# Reference: Unicode Meetei Mayek block (U+ABC0–U+ABFF).

_CONSONANTS = {
    "ক": "ꯀ", "খ": "ꯈ", "গ": "ꯒ", "ঘ": "ꯘ", "ঙ": "ꯉ",
    "চ": "ꯆ", "ছ": "ꯆ", "জ": "ꯖ", "ঝ": "ꯓ", "ঞ": "ꯅ",
    "ট": "ꯇ", "ঠ": "ꯊ", "ড": "ꯗ", "ঢ": "ꯙ", "ণ": "ꯅ",
    "ত": "ꯇ", "থ": "ꯊ", "দ": "ꯗ", "ধ": "ꯙ", "ন": "ꯅ",
    "প": "ꯄ", "ফ": "ꯐ", "ব": "ꯕ", "ভ": "ꯚ", "ম": "ꯃ",
    "য": "ꯌ", "র": "ꯔ", "ল": "ꯂ",
    "শ": "ꯁ", "ষ": "ꯁ", "স": "ꯁ", "হ": "ꯍ", "ৱ": "ꯋ",
    "য়": "ꯌ", "ড়": "ꯗ", "ঢ়": "ꯙ",
}

_INDEPENDENT_VOWELS = {
    "অ": "ꯑ",
    "আ": "ꯑꯥ",
    "ই": "ꯏ", "ঈ": "ꯏ",
    "উ": "ꯎ", "ঊ": "ꯎ",
    "এ": "ꯑꯦ", "ঐ": "ꯑꯩ",
    "ও": "ꯑꯣ", "ঔ": "ꯑꯧ",
}

_VOWEL_SIGNS = {
    "া": "ꯥ", "ি": "ꯤ", "ী": "ꯤ",
    "ু": "ꯨ", "ূ": "ꯨ",
    "ে": "ꯦ", "ৈ": "ꯩ",
    "ো": "ꯣ", "ৌ": "ꯧ",
}

_VIRAMA = "্"          # Bengali halant
_MEETEI_VIRAMA = "꯭"   # Meetei Mayek apun iyek

_DIGITS = {
    "০": "꯰", "১": "꯱", "২": "꯲", "৩": "꯳", "৪": "꯴",
    "৫": "꯵", "৬": "꯶", "৭": "꯷", "৮": "꯸", "৯": "꯹",
}


def _manual_translit(text: str) -> str:
    out = []
    for ch in text:
        if ch in _CONSONANTS:
            out.append(_CONSONANTS[ch])
        elif ch in _INDEPENDENT_VOWELS:
            out.append(_INDEPENDENT_VOWELS[ch])
        elif ch in _VOWEL_SIGNS:
            out.append(_VOWEL_SIGNS[ch])
        elif ch == _VIRAMA:
            out.append(_MEETEI_VIRAMA)
        elif ch in _DIGITS:
            out.append(_DIGITS[ch])
        else:
            out.append(ch)  # English letters, punctuation, math, spaces stay
    return "".join(out)
