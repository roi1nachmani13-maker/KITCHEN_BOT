"""
Tests for Google Sheets managers (with mocked client).
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from src.sheets.completions import CompletionsManager
from src.sheets.inventory import InventoryManager


class TestCompletionsManager:
    @pytest.fixture
    def manager(self):
        return CompletionsManager()

    def test_get_active_filters_cancelled(self, manager):
        records = [
            {"שם מוצר": "חלב", "סטטוס": "פתוח"},
            {"שם מוצר": "עגבניות", "סטטוס": "בוטל"},
            {"שם מוצר": "מוצרלה", "סטטוס": "נקנה"},
        ]
        with patch("src.sheets.completions.sheets_client") as mock:
            mock.get_all_records.return_value = records
            result = manager.get_active()
        assert len(result) == 2
        assert all(r["סטטוס"] != "בוטל" for r in result)

    def test_find_item_returns_active(self, manager):
        records = [
            {"שם מוצר": "חלב", "סטטוס": "פתוח", "כמות חסרה": "2"},
        ]
        with patch("src.sheets.completions.sheets_client") as mock:
            mock.get_all_records.return_value = records
            result = manager.find_item("חלב")
        assert result is not None
        assert result["שם מוצר"] == "חלב"

    def test_find_item_returns_none_if_cancelled(self, manager):
        records = [{"שם מוצר": "חלב", "סטטוס": "בוטל"}]
        with patch("src.sheets.completions.sheets_client") as mock:
            mock.get_all_records.return_value = records
            result = manager.find_item("חלב")
        assert result is None

    def test_daily_stats(self, manager):
        records = [
            {"סטטוס": "פתוח"},
            {"סטטוס": "פתוח"},
            {"סטטוס": "נקנה"},
            {"סטטוס": "בוטל"},
        ]
        with patch("src.sheets.completions.sheets_client") as mock:
            mock.get_all_records.return_value = records
            stats = manager.get_daily_stats()
        assert stats["פתוח"] == 2
        assert stats["נקנה"] == 1
        assert stats["בוטל"] == 1
        assert stats['סה"כ'] == 4


class TestInventoryManager:
    @pytest.fixture
    def manager(self):
        return InventoryManager()

    def test_get_all_active_filters_disabled(self, manager):
        records = [
            {"שם מוצר": "חלב", "פעיל": "TRUE"},
            {"שם מוצר": "גבינה ישנה", "פעיל": "FALSE"},
        ]
        with patch("src.sheets.inventory.sheets_client") as mock:
            mock.get_all_records.return_value = records
            result = manager.get_all_active()
        assert len(result) == 1
        assert result[0]["שם מוצר"] == "חלב"

    def test_get_product_names(self, manager):
        records = [
            {"שם מוצר": "חלב", "פעיל": "TRUE"},
            {"שם מוצר": "עגבניות", "פעיל": "TRUE"},
        ]
        with patch("src.sheets.inventory.sheets_client") as mock:
            mock.get_all_records.return_value = records
            names = manager.get_all_product_names()
        assert "חלב" in names
        assert "עגבניות" in names

    def test_get_product_not_found(self, manager):
        with patch("src.sheets.inventory.sheets_client") as mock:
            mock.get_all_records.return_value = []
            result = manager.get_product("חלב")
        assert result is None
