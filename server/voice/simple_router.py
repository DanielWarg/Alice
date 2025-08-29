# -*- coding: utf-8 -*-
# voice/simple_router.py
import re
from typing import Literal
from .simple_normalizer import pre_normalize_sv, post_normalize_en

# Sv datum/tid/dagar-mönster för att avgöra "enklare" vs "komplex"
_DATE_TIME_HINTS = re.compile(
    r"(idag|imorgon|i övermorgon|igår|i förrgår|måndag|tisdag|onsdag|torsdag|fredag|lördag|söndag|"
    r"om\s+\d+\s+(minut|timm|dag|veck|mån|år)|\bklockan\b|\bkl\.?\b|midsommarafton)",
    flags=re.I
)

def is_simple_text_sv(text_sv: str, max_len: int = 80) -> bool:
    """Korta, enkla fraser utan datum/tid → snabbspår."""
    if len(text_sv.strip()) > max_len:
        return False
    if _DATE_TIME_HINTS.search(text_sv):
        return False
    return True

def choose_model_for_sv(text_sv: str) -> Literal["llama3:8b", "gpt-oss:20b"]:
    """Router: 8B för kort/enkelt, annars 20B."""
    return "llama3:8b" if is_simple_text_sv(text_sv) else "gpt-oss:20b"