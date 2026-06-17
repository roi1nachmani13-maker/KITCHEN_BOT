"""
Main NLP parser: turns free-form Hebrew messages into structured actions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, List

from src.nlp.intents import Intent, detect_intent_prefix
from src.nlp.fuzzy import find_best_match, suggest_correction
from src.utils.logger import get_logger

log = get_logger(__name__)

# Matches a trailing number (int or float) possibly with Hebrew units
# e.g. "חלב 2", "עגבניות 1.5", "שמן 3 ליטר"
_QTY_RE = re.compile(
    r"^(.*?)\s+(\d+(?:\.\d+)?)"   # name then number
    r"(?:\s+(.+))?$"               # optional unit after number
)

# Common Hebrew units
HEBREW_UNITS = {
    "קג": "ק\"ג",
    'ק"ג': "ק\"ג",
    "קילו": "ק\"ג",
    "ליטר": "ליטר",
    "ל": "ליטר",
    "חבילה": "חבילה",
    "חבילות": "חבילות",
    "יחידה": "יח'",
    "יחידות": "יח'",
    "יח": "יח'",
    "גרם": "גרם",
    "גר": "גרם",
    "מ\"ל": "מ\"ל",
    "מל": "מ\"ל",
}


@dataclass
class ParsedMessage:
    intent: Intent
    product_name: str
    quantity: float = 1.0
    unit: Optional[str] = None
    original_text: str = ""
    confidence: float = 1.0          # 1.0 = exact, 0.x = fuzzy
    suggestion: Optional[str] = None  # if fuzzy matched, the canonical name
    matched_name: Optional[str] = None  # resolved canonical name from inventory


def _normalize_unit(raw: str) -> Optional[str]:
    if not raw:
        return None
    key = raw.strip().lower().replace('"', '"')
    return HEBREW_UNITS.get(key, raw.strip())


def _extract_name_and_qty(text: str) -> tuple[str, float, Optional[str]]:
    """
    Extract product name, quantity, and optional unit from text.
    Examples:
        "חלב"           -> ("חלב", 1.0, None)
        "חלב 2"         -> ("חלב", 2.0, None)
        "עגבניות 5 קג"  -> ("עגבניות", 5.0, 'ק"ג')
    """
    m = _QTY_RE.match(text.strip())
    if m:
        name = m.group(1).strip()
        qty = float(m.group(2))
        unit_raw = m.group(3)
        unit = _normalize_unit(unit_raw) if unit_raw else None
        return name, qty, unit

    # No number found — whole text is the product name
    return text.strip(), 1.0, None


class MessageParser:
    """Parses a Telegram message into a ParsedMessage."""

    def __init__(self, product_names: Optional[List[str]] = None) -> None:
        self._product_names: List[str] = product_names or []

    def update_product_names(self, names: List[str]) -> None:
        self._product_names = names

    def parse(self, text: str) -> Optional[ParsedMessage]:
        """
        Parse a free-form Hebrew message.
        Returns None if the message doesn't look like an inventory action.
        """
        text = text.strip()
        if not text:
            return None

        # Skip messages that look like commands (/...)
        if text.startswith("/"):
            return None

        intent, remainder = detect_intent_prefix(text)
        product_name_raw, qty, unit = _extract_name_and_qty(remainder)

        if not product_name_raw:
            return None

        # Try to resolve against known inventory
        matched_name = None
        confidence = 1.0
        suggestion = None

        if self._product_names:
            # Check exact match first
            exact = next(
                (n for n in self._product_names
                 if n.strip().lower() == product_name_raw.strip().lower()),
                None
            )
            if exact:
                matched_name = exact
                confidence = 1.0
            else:
                # Fuzzy match
                fuzzy_name, score = find_best_match(product_name_raw, self._product_names)
                if fuzzy_name:
                    matched_name = fuzzy_name
                    confidence = score / 100.0
                    if confidence < 0.95:
                        suggestion = fuzzy_name
                else:
                    # No match — still parse but flag it
                    matched_name = product_name_raw
                    confidence = 0.5
                    suggestion = suggest_correction(product_name_raw, self._product_names)

        else:
            matched_name = product_name_raw

        return ParsedMessage(
            intent=intent,
            product_name=matched_name or product_name_raw,
            quantity=qty,
            unit=unit,
            original_text=text,
            confidence=confidence,
            suggestion=suggestion,
            matched_name=matched_name,
        )


# Module-level instance (product names loaded at startup)
parser = MessageParser()


# Import COUNT intent support
from src.nlp.intents import Intent as _Intent
