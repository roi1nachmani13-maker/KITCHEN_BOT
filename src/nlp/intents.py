"""
Intent definitions and keyword patterns for Hebrew NLP.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import List


class Intent(str, Enum):
    ADD = "add"
    MARK_DONE = "mark_done"
    CANCEL = "cancel"
    RESTORE = "restore"
    COUNT = "count"
    UNKNOWN = "unknown"


# ---- Intent keyword patterns ----

ADD_PATTERNS: List[str] = [
    r"^צריך\s",
    r"^תוסיף\s",
    r"^חסר\s",
    r"^חסרה\s",
    r"^חסרים\s",
    r"^נגמר\s",
    r"^נגמרה\s",
    r"^אין\s",
    r"^הוסף\s",
    r"^להוסיף\s",
]

DONE_PATTERNS: List[str] = [
    r"^קניתי\s",
    r"^קנינו\s",
    r"^הגיע\s",
    r"^הגיעה\s",
    r"^הבאתי\s",
    r"^הבאנו\s",
    r"^הושלם\s",
    r"^הושלמה\s",
    r"^נקנה\s",
    r"^יש\s",
    r"^סיימנו\s",
]

CANCEL_PATTERNS: List[str] = [
    r"^לא צריך\s",
    r"^לא צריכים\s",
    r"^הסר\s",
    r"^תמחק\s",
    r"^מחק\s",
    r"^בטל\s",
    r"^ביטול\s",
    r"^תבטל\s",
]

RESTORE_PATTERNS: List[str] = [
    r"^החזר\s",
    r"^תחזיר\s",
    r"^תשחזר\s",
    r"^שחזר\s",
]

_COMPILED: dict = {}


def _compile_patterns() -> None:
    global _COMPILED
    _COMPILED = {
        Intent.ADD: [re.compile(p, re.IGNORECASE) for p in ADD_PATTERNS],
        Intent.MARK_DONE: [re.compile(p, re.IGNORECASE) for p in DONE_PATTERNS],
        Intent.CANCEL: [re.compile(p, re.IGNORECASE) for p in CANCEL_PATTERNS],
        Intent.RESTORE: [re.compile(p, re.IGNORECASE) for p in RESTORE_PATTERNS],
    }


_compile_patterns()


def detect_intent_prefix(text: str) -> tuple[Intent, str]:
    """
    Detect intent from leading keywords.
    Returns (intent, remaining_text_after_keyword).
    """
    text = text.strip()
    for intent, patterns in _COMPILED.items():
        for pattern in patterns:
            m = pattern.match(text)
            if m:
                remaining = text[m.end():].strip()
                return intent, remaining

    # No keyword prefix - treat as ADD (bare product name/qty)
    return Intent.ADD, text


# ---- Evening count patterns ----
COUNT_PATTERNS: List[str] = [
    r"^נשאר\s",
    r"^נשארה\s",
    r"^נשארו\s",
    r"^יש\s",
    r"^נותר\s",
    r"^נותרה\s",
    r"^נותרו\s",
    r"^ספירה\s",
]


def _add_count_patterns() -> None:
    global _COMPILED
    _COMPILED[Intent.COUNT] = [re.compile(p, re.IGNORECASE) for p in COUNT_PATTERNS]


_add_count_patterns()
