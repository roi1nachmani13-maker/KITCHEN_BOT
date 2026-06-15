"""
Permanent inventory management (מלאי קבוע).
"""
from __future__ import annotations

import uuid
from typing import List, Dict, Optional

from src.sheets.client import sheets_client, SHEET_INVENTORY, INVENTORY_HEADERS
from src.utils.logger import get_logger

log = get_logger(__name__)


class InventoryManager:
    """CRUD operations for the permanent inventory sheet."""

    def get_all_active(self) -> List[Dict]:
        """Return all active (non-disabled) products."""
        records = sheets_client.get_all_records(SHEET_INVENTORY)
        return [r for r in records if str(r.get("פעיל", "TRUE")).upper() != "FALSE"]

    def get_all(self) -> List[Dict]:
        """Return all products including disabled."""
        return sheets_client.get_all_records(SHEET_INVENTORY)

    def get_product(self, name: str) -> Optional[Dict]:
        """Find product by name (exact, case-insensitive)."""
        records = sheets_client.get_all_records(SHEET_INVENTORY)
        for r in records:
            if r.get("שם מוצר", "").strip().lower() == name.strip().lower():
                return r
        return None

    def get_all_product_names(self) -> List[str]:
        """Return names of all active products (for fuzzy matching)."""
        return [r.get("שם מוצר", "") for r in self.get_all_active()]

    def add_product(
        self,
        name: str,
        category: str = "כללי",
        target_qty: str = "",
        unit: str = "",
        notes: str = "",
    ) -> Dict:
        """Add a new product to permanent inventory."""
        product_id = str(uuid.uuid4())[:8].upper()
        row = [
            product_id,  # מזהה מוצר
            name,         # שם מוצר
            category,     # קטגוריה
            target_qty,   # כמות יעד
            unit,         # יחידת מידה
            "TRUE",       # פעיל
            notes,        # הערות
        ]
        sheets_client.append_row(SHEET_INVENTORY, row)
        log.info(f"Added product: {name} [{product_id}]")
        return {"מזהה מוצר": product_id, "שם מוצר": name, "קטגוריה": category}

    def disable_product(self, name: str) -> bool:
        """Disable a product (soft delete)."""
        row_idx = sheets_client.find_row_index(SHEET_INVENTORY, "שם מוצר", name)
        if row_idx is None:
            return False
        active_col = INVENTORY_HEADERS.index("פעיל") + 1
        sheets_client.update_cell(SHEET_INVENTORY, row_idx, active_col, "FALSE")
        log.info(f"Disabled product: {name}")
        return True

    def enable_product(self, name: str) -> bool:
        """Re-enable a disabled product."""
        row_idx = sheets_client.find_row_index(SHEET_INVENTORY, "שם מוצר", name)
        if row_idx is None:
            return False
        active_col = INVENTORY_HEADERS.index("פעיל") + 1
        sheets_client.update_cell(SHEET_INVENTORY, row_idx, active_col, "TRUE")
        log.info(f"Enabled product: {name}")
        return True

    def get_product_with_unit(self, name: str) -> tuple[Optional[str], Optional[str]]:
        """Return (unit, category) for a product name, or (None, None)."""
        product = self.get_product(name)
        if product:
            return product.get("יחידת מידה", ""), product.get("קטגוריה", "כללי")
        return None, None


inventory_manager = InventoryManager()
