"""
Fuzzy product name matching for Hebrew typos and variations.
"""
from __future__ import annotations

from typing import Optional, Tuple

from rapidfuzz import process, fuzz

from src.utils.config import config
from src.utils.logger import get_logger

log = get_logger(__name__)


def find_best_match(
    query: str,
    candidates: list[str],
    threshold: Optional[int] = None,
) -> Tuple[Optional[str], int]:
    """
    Find the best matching product name.

    Returns:
        (matched_name, score) or (None, 0) if no match above threshold.
    """
    if not candidates:
        return None, 0

    threshold = threshold or config.fuzzy_threshold

    result = process.extractOne(
        query,
        candidates,
        scorer=fuzz.WRatio,  # handles partial matches, transpositions, etc.
    )

    if result is None:
        return None, 0

    name, score, _ = result
    if score >= threshold:
        log.debug(f"Fuzzy match: '{query}' -> '{name}' ({score})")
        return name, score

    return None, score


def suggest_correction(query: str, candidates: list[str]) -> Optional[str]:
    """
    Return a suggestion string like 'התכוונת ל-מוצרלה?' or None.
    Uses a lower threshold for suggestions vs actual matching.
    """
    name, score = find_best_match(query, candidates, threshold=60)
    if name and name.lower() != query.lower():
        return name
    return None
