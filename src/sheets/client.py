"""
Google Sheets base client with retry logic and sheet initialization.
"""
from __future__ import annotations

import time
from typing import List, Dict, Optional, Any

import gspread
from google.oauth2.service_account import Credentials
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from gspread.exceptions import APIError

from src.utils.config import config
from src.utils.logger import get_logger

log = get_logger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sheet names
SHEET_INVENTORY = "מלאי קבוע"
SHEET_COMPLETIONS = "השלמות להיום"
SHEET_HISTORY = "היסטוריה"
SHEET_EVENING = "ספירת ערב"
SHEET_AUTO_COMPLETIONS = "השלמות אוטומטיות"

# Column definitions
INVENTORY_HEADERS = [
    "מזהה מוצר", "שם מוצר", "קטגוריה", "כמות יעד",
    "יחידת מידה", "פעיל", "הערות"
]

COMPLETIONS_HEADERS = [
    "תאריך", "שעה", "שם מוצר", "כמות חסרה",
    "יחידת מידה", "קטגוריה", "מי דיווח", "מקור הודעה",
    "סטטוס", "הערות"
]

HISTORY_HEADERS = [
    "תאריך", "שעה", "פעולה", "שם מוצר", "כמות",
    "יחידת מידה", "מי ביצע", "הודעה מקורית", "פרטים נוספים"
]


class SheetsClient:
    """Thin wrapper around gspread with helpers."""

    def __init__(self) -> None:
        self._gc: Optional[gspread.Client] = None
        self._spreadsheet: Optional[gspread.Spreadsheet] = None
        self._sheets: Dict[str, gspread.Worksheet] = {}

    def connect(self) -> None:
        """Authenticate and open spreadsheet."""
        creds_info = config.get_service_account_info()
        creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
        self._gc = gspread.authorize(creds)
        self._spreadsheet = self._gc.open_by_key(config.spreadsheet_id)
        log.info(f"Connected to spreadsheet: {self._spreadsheet.title}")
        self._ensure_sheets()

    def _ensure_sheets(self) -> None:
        """Create sheets if they don't exist and cache references."""
        existing = {ws.title: ws for ws in self._spreadsheet.worksheets()}

        for title, headers in [
            (SHEET_INVENTORY, INVENTORY_HEADERS),
            (SHEET_COMPLETIONS, COMPLETIONS_HEADERS),
            (SHEET_HISTORY, HISTORY_HEADERS),
        ]:
            if title not in existing:
                ws = self._spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
                ws.append_row(headers, value_input_option="RAW")
                # Format header row
                ws.format("1:1", {
                    "textFormat": {"bold": True},
                    "backgroundColor": {"red": 0.9, "green": 0.9, "blue": 0.9}
                })
                log.info(f"Created sheet: {title}")
            else:
                ws = existing[title]
            self._sheets[title] = ws

    def sheet(self, name: str) -> gspread.Worksheet:
        if name not in self._sheets:
            raise ValueError(f"Sheet '{name}' not found. Call connect() first.")
        return self._sheets[name]

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def get_all_records(self, sheet_name: str) -> List[Dict]:
        """Return all rows as list of dicts."""
        ws = self.sheet(sheet_name)
        return ws.get_all_records(default_blank="")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def append_row(self, sheet_name: str, row: List[Any]) -> None:
        """Append a single row."""
        ws = self.sheet(sheet_name)
        ws.append_row(row, value_input_option="USER_ENTERED")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def update_cell(self, sheet_name: str, row: int, col: int, value: Any) -> None:
        """Update a single cell (1-indexed)."""
        ws = self.sheet(sheet_name)
        ws.update_cell(row, col, value)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(APIError),
    )
    def update_row(self, sheet_name: str, row_index: int, values: List[Any]) -> None:
        """Update an entire row (1-indexed, including header)."""
        ws = self.sheet(sheet_name)
        col_count = len(values)
        cell_range = f"A{row_index}:{chr(64 + col_count)}{row_index}"
        ws.update(cell_range, [values], value_input_option="USER_ENTERED")

    def find_row_index(self, sheet_name: str, col_name: str, value: str) -> Optional[int]:
        """
        Find row index (1-based, including header row) for first match.
        Returns None if not found.
        """
        records = self.get_all_records(sheet_name)
        for i, record in enumerate(records, start=2):  # row 1 = header
            if str(record.get(col_name, "")).strip().lower() == value.strip().lower():
                return i
        return None

    def clear_sheet_data(self, sheet_name: str) -> None:
        """Clear all data rows (keep header)."""
        ws = self.sheet(sheet_name)
        # Get current row count
        all_vals = ws.get_all_values()
        if len(all_vals) > 1:
            ws.delete_rows(2, len(all_vals))
        log.info(f"Cleared data in sheet: {sheet_name}")

    def duplicate_sheet_as_archive(self, sheet_name: str, archive_title: str) -> None:
        """Copy a sheet as an archive tab."""
        ws = self.sheet(sheet_name)
        ws.copy_to(self._spreadsheet.id)
        # Rename the copy
        sheets = self._spreadsheet.worksheets()
        for s in sheets:
            if s.title == f"Copy of {ws.title}":
                s.update_title(archive_title)
                break
        log.info(f"Archived sheet as: {archive_title}")


# Module-level singleton
sheets_client = SheetsClient()
