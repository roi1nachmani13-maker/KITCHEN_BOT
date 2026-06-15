"""
History / audit log management (היסטוריה).
"""
from __future__ import annotations

from typing import List, Dict, Optional

from src.sheets.client import sheets_client, SHEET_HISTORY
from src.utils.formatters import format_date, format_time
from src.utils.logger import get_logger

log = get_logger(__name__)


class HistoryManager:
    """Append-only audit log."""

    def log_action(
        self,
        action: str,
        product_name: str,
        actor: str,
        original_message: str = "",
        qty: str = "",
        unit: str = "",
        details: str = "",
    ) -> None:
        """Write one row to the history sheet."""
        row = [
            format_date(),       # תאריך
            format_time(),       # שעה
            action,              # פעולה
            product_name,        # שם מוצר
            qty,                 # כמות
            unit,                # יחידת מידה
            actor,               # מי ביצע
            original_message,    # הודעה מקורית
            details,             # פרטים נוספים
        ]
        sheets_client.append_row(SHEET_HISTORY, row)
        log.debug(f"History: [{action}] {product_name} by {actor}")

    def get_product_history(self, name: str) -> List[Dict]:
        """Return all history rows for a given product name."""
        records = sheets_client.get_all_records(SHEET_HISTORY)
        return [
            r for r in records
            if r.get("שם מוצר", "").strip().lower() == name.strip().lower()
        ]

    def get_last_update(self, name: str) -> Optional[Dict]:
        """Return the most recent history entry for a product."""
        history = self.get_product_history(name)
        if not history:
            return None
        return history[-1]


history_manager = HistoryManager()
