"""
Evening count management (ספירת ערב).
Workers report what's left, system calculates what's missing.
"""
from __future__ import annotations

from typing import List, Dict, Optional

from src.sheets.client import sheets_client
from src.utils.formatters import format_date, format_time
from src.utils.logger import get_logger

log = get_logger(__name__)

SHEET_EVENING = "ספירת ערב"
SHEET_COMPLETIONS_AUTO = "השלמות אוטומטיות"

EVENING_HEADERS = ["תאריך", "שם מוצר", "כמות שנשארה", "יחידה", "מי ספר"]


class EveningCountManager:

    def update_count(self, product_name: str, qty: float, reporter: str, unit: str = "") -> Dict:
        """Add or update evening count for a product."""
        records = sheets_client.get_all_records(SHEET_EVENING)
        today = format_date()

        # Check if already reported today
        for i, r in enumerate(records, start=2):
            if (
                r.get("שם מוצר", "").strip().lower() == product_name.strip().lower()
                and r.get("תאריך", "") == today
            ):
                # Update existing
                from src.sheets.client import SHEET_EVENING as SE
                sheets_client.update_cell(SHEET_EVENING, i, 3, qty)
                log.info(f"Updated evening count: {product_name} = {qty}")
                return {"action": "updated", "name": product_name, "qty": qty}

        # Add new row
        row = [today, product_name, qty, unit, reporter]
        sheets_client.append_row(SHEET_EVENING, row)

        # Update auto-completions sheet
        self._update_auto_completions(product_name, qty)

        log.info(f"Added evening count: {product_name} = {qty}")
        return {"action": "added", "name": product_name, "qty": qty}

    def _update_auto_completions(self, product_name: str, qty: float) -> None:
        """Update the 'כמות שנשארה' column in auto-completions sheet."""
        try:
            records = sheets_client.get_all_records(SHEET_COMPLETIONS_AUTO)
            for i, r in enumerate(records, start=2):
                if r.get("שם המוצר", "").strip().lower() == product_name.strip().lower() or \
                   r.get("שם מוצר", "").strip().lower() == product_name.strip().lower():
                    sheets_client.update_cell(SHEET_COMPLETIONS_AUTO, i, 3, qty)
                    log.info(f"Updated auto-completions: {product_name} remaining = {qty}")
                    return
        except Exception as e:
            log.warning(f"Could not update auto-completions: {e}")

    def get_today_counts(self) -> List[Dict]:
        """Get all counts for today."""
        today = format_date()
        records = sheets_client.get_all_records(SHEET_EVENING)
        return [r for r in records if r.get("תאריך", "") == today]

    def get_missing_items(self) -> List[Dict]:
        """Get items that are missing based on auto-completions."""
        try:
            records = sheets_client.get_all_records(SHEET_COMPLETIONS_AUTO)
            return [r for r in records if r.get("סטטוס", "") == "חסר"]
        except Exception as e:
            log.error(f"Error getting missing items: {e}")
            return []


evening_manager = EveningCountManager()
