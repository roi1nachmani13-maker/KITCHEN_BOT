#!/usr/bin/env python3
"""
One-time setup script: creates the Google Sheet with correct tabs and headers,
and populates a sample inventory for testing.

Run:
    python scripts/setup_sheets.py
"""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.sheets.client import sheets_client
from src.sheets.inventory import inventory_manager
from src.utils.config import config
from src.utils.logger import get_logger

log = get_logger("setup")

SAMPLE_PRODUCTS = [
    # (name, category, target_qty, unit)
    ("עגבניות", "ירקות ופירות", "10", 'ק"ג'),
    ("חלב", "גבינות ומוצרי חלב", "6", "ליטר"),
    ("מוצרלה", "גבינות ומוצרי חלב", "4", 'ק"ג'),
    ("בזיליקום", "ירקות ופירות", "2", "חבילה"),
    ("שמן זית", "יבש ושימורים", "3", "ליטר"),
    ("ביצים", "גבינות ומוצרי חלב", "30", "יח'"),
    ("לימון", "ירקות ופירות", "10", "יח'"),
    ("שום", "ירקות ופירות", "1", 'ק"ג'),
    ("פסטה", "יבש ושימורים", "5", 'ק"ג'),
    ("קמח", "יבש ושימורים", "5", 'ק"ג'),
    ("סוכר", "יבש ושימורים", "2", 'ק"ג'),
    ("מלח", "יבש ושימורים", "1", 'ק"ג'),
    ("חמאה", "גבינות ומוצרי חלב", "500", "גרם"),
    ("שמנת מתוקה", "גבינות ומוצרי חלב", "1", "ליטר"),
    ("עוף שלם", "בשר ודגים", "5", "יח'"),
]


def main() -> None:
    print(f"🔧 Kitchen Bot – Sheet Setup")
    print(f"   Spreadsheet ID: {config.spreadsheet_id}")
    print()

    config.validate()

    print("📡 Connecting to Google Sheets...")
    sheets_client.connect()
    print("✅ Connected!\n")

    print("📦 Adding sample inventory products...")
    for name, category, target, unit in SAMPLE_PRODUCTS:
        existing = inventory_manager.get_product(name)
        if existing:
            print(f"   ⏭  {name} (already exists)")
        else:
            inventory_manager.add_product(name, category=category, target_qty=target, unit=unit)
            print(f"   ✅ Added: {name} [{category}] {target} {unit}")

    print()
    print("🎉 Setup complete!")
    print(f"   Open your spreadsheet: https://docs.google.com/spreadsheets/d/{config.spreadsheet_id}")
    print()
    print("Next steps:")
    print("  1. Copy .env.example to .env and fill in your tokens")
    print("  2. Run: docker-compose up -d")
    print("  3. Add the bot to your Telegram group")
    print("  4. Send 'חלב 2' to test!")


if __name__ == "__main__":
    main()
