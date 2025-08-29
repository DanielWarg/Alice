# -*- coding: utf-8 -*-
# voice/simple_normalizer.py
import re
from typing import Tuple

# --- PRE: SV -> enklare/mindre felbenägen text för LLM ---

_WEEKDAYS_SV_EN = {
    "måndag": "Monday", "tisdag": "Tuesday", "onsdag": "Wednesday",
    "torsdag": "Thursday", "fredag": "Friday", "lördag": "Saturday",
    "söndag": "Sunday"
}
_RELATIVE_SV_EN = {
    r"\bidag\b": "today",
    r"\bimorgon\b": "tomorrow",
    r"\bi övermorgon\b": "the day after tomorrow",
    r"\bigår\b": "yesterday",
    r"\bi förrgår\b": "the day before yesterday",
    r"\bmidsommarafton\b": "Midsummer Eve"
}
# om X minuter/timmar/dagar/veckor/månader/år
_RELATIVE_NUM_PATTERNS = [
    (re.compile(r"\bom\s+(\d+)\s+minut(?:er)?\b", re.I), r"in \1 minutes"),
    (re.compile(r"\bom\s+(\d+)\s+timm(?:e|ar)\b", re.I),  r"in \1 hours"),
    (re.compile(r"\bom\s+(\d+)\s+dagar?\b", re.I),        r"in \1 days"),
    (re.compile(r"\bom\s+(\d+)\s+veckor?\b", re.I),       r"in \1 weeks"),
    (re.compile(r"\bom\s+(\d+)\s+månader?\b", re.I),      r"in \1 months"),
    (re.compile(r"\bom\s+(\d+)\s+år\b", re.I),            r"in \1 years"),
]

def pre_normalize_sv(text_sv: str) -> str:
    """
    Lättvikts-normalisering av svenska tidsfraser före LLM.
    Ja, det blir delvis engelska tokens – medvetet för att minska hallucinationer.
    """
    t = text_sv

    # Veckodagar
    for sv, en in _WEEKDAYS_SV_EN.items():
        t = re.sub(rf"\b{sv}\b", en, t, flags=re.I)

    # Relativa ord
    for pat, repl in _RELATIVE_SV_EN.items():
        t = re.sub(pat, repl, t, flags=re.I)

    # "om X ...": in 10 minutes/hours/days/...
    for rx, repl in _RELATIVE_NUM_PATTERNS:
        t = rx.sub(repl, t)

    # "kl 10" / "klockan 10" -> "at 10"
    t = re.sub(r"\bklockan\b\s*(\d{1,2})(:\d{2})?", r"at \1\2", t, flags=re.I)
    t = re.sub(r"\bkl\.?\b\s*(\d{1,2})(:\d{2})?",   r"at \1\2", t, flags=re.I)

    # Whitespace-städ
    t = re.sub(r"\s+", " ", t).strip()
    return t

# --- POST: EN -> kanonisering innan TTS/cache ---

_UNITS = {
    "zero":0,"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,"nine":9,
    "ten":10,"eleven":11,"twelve":12,"thirteen":13,"fourteen":14,"fifteen":15,"sixteen":16,
    "seventeen":17,"eighteen":18,"nineteen":19
}
_TENS = {"twenty":20,"thirty":30,"forty":40,"fifty":50,"sixty":60,"seventy":70,"eighty":80,"ninety":90}

def _words_0_99_to_num(m: re.Match) -> str:
    tens = m.group(1).lower()
    unit = m.group(2).lower()
    return str(_TENS.get(tens, 0) + _UNITS.get(unit, 0))

def _word_num_to_digit(match: re.Match) -> str:
    w = match.group(0).lower()
    return str(_UNITS[w])

def _tens_to_digit(match: re.Match) -> str:
    w = match.group(0).lower()
    return str(_TENS[w])

def _normalize_emails(text: str) -> str:
    # "mail/mails" -> "email/emails" i vanliga påståenden
    text = re.sub(r"\bmail\b",  "email", text, flags=re.I)
    text = re.sub(r"\bmails\b", "emails", text, flags=re.I)
    return text

def _ensure_final_punctuation(text: str) -> str:
    return text if re.search(r"[.!?]$", text) else (text.rstrip() + ".")

def post_normalize_en(speak_text_en: str) -> str:
    """
    Gör TTS-text konsekvent och cache-vänlig:
    - Skriv siffror (0–99) med digits
    - Standardisera 'email(s)'
    - Trimma whitespace och avsluta med punkt om saknas
    """
    t = speak_text_en.strip()

    # two-word numbers "twenty one" / "twenty-one"
    t = re.sub(
        r"\b(" + "|".join(_TENS.keys()) + r")[ -](" + "|".join(_UNITS.keys()) + r")\b",
        _words_0_99_to_num, t, flags=re.I
    )
    # single tens
    t = re.sub(r"\b(" + "|".join(_TENS.keys()) + r")\b", _tens_to_digit, t, flags=re.I)
    # single 0..19
    t = re.sub(r"\b(" + "|".join(_UNITS.keys()) + r")\b", _word_num_to_digit, t, flags=re.I)

    # email(s)
    t = _normalize_emails(t)

    # collapse spaces and add period
    t = re.sub(r"\s+", " ", t).strip()
    t = _ensure_final_punctuation(t)
    return t

# --- Hjälpare för cache-nyckel ---

def make_cache_key(voice: str, rate: float, speak_text_en: str) -> str:
    # OBS: för runtime-hash kan du md5/sha1'a denna sträng.
    base = f"{voice}|{rate}|{post_normalize_en(speak_text_en)}"
    return base