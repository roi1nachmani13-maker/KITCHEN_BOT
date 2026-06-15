"""
Daily completions management (השלמות להיום).
"""
from __future__ import annotations

from typing import List, Dict, Optional

from src.sheets.client import sheets_client, SHEET_COMPLETIONS, COMPLETIONS_HEADERS
from src.sheets.inventory import inventory_manager
from src.utils.formatters import format_date, format_time
from src.utils.logger import get_logger

log = get_logger(__name__)

VALID_STATUSES = {"פתוח", "בטיפול", "נקנה", "בוטל", "הוחזר"}


class CompletionsManager:
    """Operations on the daily completions sheet."""

    def get_active(self) -> List[Dict]:
        """Return items not cancelled."""
        records = sheets_client.get_all_records(SHEET_COMPLETIONS)
        return [r for r in records if r.get("סטטוס") != "בוטל"]

    def get_all(self) -> List[Dict]:
        return sheets_client.get_all_records(SHEET_COMPLETIONS)

    def find_item(self, name: str) -> Optional[Dict]:
        """Find active item by name."""
        for item in self.get_active():
            if item.get("שם מוצר", "").strip().lower() == name.strip().lower():
                return item
        return None

    def find_item_row(self, name: str) -> Optional[int]:
        """Find row index (1-based) of active item by name."""
        records = sheets_client.get_all_records(SHEET_COMPLETIONS)
        for i, r in enumerate(records, start=2):
            if (
                r.get("שם מוצר", "").strip().lower() == name.strip().lower()
                and r.get("סטטוס") != "בוטל"
            ):
                return i
        return None

    def add_or_update(
        self,
        name: str,
        qty: float,
        reporter: str,
        source: str = "telegram",
        notes: str = "",
    ) -> Dict:
        """
        Add item or accumulate quantity if already exists.
        Returns dict with 'action' ('added' | 'updated') and item info.
        """
        unit, category = inventory_manager.get_product_with_unit(name)
        unit = unit or ""
        category = category or "כללי"

        existing_row = self.find_item_row(name)

        if existing_row is not None:
            # Accumulate quantity
            existing = sheets_client.get_all_records(SHEET_COMPLETIONS)[existing_row - 2]
            old_qty = float(existing.get("כמות חסרה", 0) or 0)
            new_qty = old_qty + qty

            qty_col = COMPLETIONS_HEADERS.index("כמות חסרה") + 1
            sheets_client.update_cell(SHEET_COMPLETIONS, existing_row, qty_col, new_qty)

            log.info(f"Updated qty: {name} {old_qty} -> {new_qty}")
            return {"action": "updated", "name": name, "old_qty": old_qty, "new_qty": new_qty, "unit": unit}

        else:
            row = [
                format_date(),    # תאריך
                format_time(),    # שעה
                name,             # שם מוצר
                qty,              # כמות חסרה
                unit,             # יחידת מידה
                category,         # קטגוריה
                reporter,         # מי דיווח
                source,           # מקור הודעה
                "פתוח",           # סטטוס
                notes,            # הערות
            ]
            sheets_client.append_row(SHEET_COMPLETIONS, row)
            log.info(f"Added completion: {name} x{qty}")
            return {"action": "added", "name": name, "qty": qty, "unit": unit}

    def set_status(self, name: str, status: str, actor: str) -> bool:
        """Update status of an item."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}")

        row_idx = self.find_item_row(name)
        if row_idx is None:
            return False

        status_col = COMPLETIONS_HEADERS.index("סטטוס") + 1
        sheets_client.update_cell(SHEET_COMPLETIONS, row_idx, status_col, status)
        log.info(f"Set status: {name} -> {status} by {actor}")
        return True

    def restore_cancelled(self, name: str) -> bool:
        """Restore a cancelled item to 'פתוח'."""
        records = sheets_client.get_all_records(SHEET_COMPLETIONS)
        for i, r in enumerate(records, start=2):
            if (
                r.get("שם מוצר", "").strip().lower() == name.strip().lower()
                and r.get("סטטוס") == "בוטל"
            ):
                status_col = COMPLETIONS_HEADERS.index("סטטוס") + 1
                sheets_client.update_cell(SHEET_COMPLETIONS, i, status_col, "הוחזר")
                log.info(f"Restored: {name}")
                return True
        return False

    def get_daily_stats(self) -> Dict:
        """Aggregate counts by status for today."""
        records = self.get_all()
        stats: Dict[str, int] = {}
        for r in records:
            s = r.get("סטטוס", "פתוח")
            stats[s] = stats.get(s, 0) + 1
        stats["סהכ"] = len(records)
        return stats

    def archive_and_clear(self, archive_title: str) -> int:
        """Archive current completions and clear the sheet."""
        records = self.get_all()
        count = len(records)
        sheets_client.duplicate_sheet_as_archive(SHEET_COMPLETIONS, archive_title)
        sheets_client.clear_sheet_data(SHEET_COMPLETIONS)
        log.info(f"Archived {count} items as '{archive_title}'")
        return count


completions_manager = CompletionsManager()
