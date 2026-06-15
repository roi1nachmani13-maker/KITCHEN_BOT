"""
Shared pytest fixtures.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.fixture
def sample_products():
    return ["חלב", "עגבניות", "מוצרלה", "בזיליקום", "שמן זית", "ביצים", "שום"]


@pytest.fixture
def mock_sheets_client():
    with patch("src.sheets.client.sheets_client") as mock:
        mock.get_all_records.return_value = []
        mock.append_row.return_value = None
        mock.update_cell.return_value = None
        yield mock


@pytest.fixture
def mock_inventory_manager(sample_products):
    with patch("src.sheets.inventory.inventory_manager") as mock:
        mock.get_all_product_names.return_value = sample_products
        mock.get_product.return_value = {"שם מוצר": "חלב", "יחידת מידה": "ליטר", "קטגוריה": "גבינות ומוצרי חלב"}
        mock.get_product_with_unit.return_value = ("ליטר", "גבינות ומוצרי חלב")
        yield mock


@pytest.fixture
def mock_telegram_update():
    update = MagicMock()
    update.effective_user.id = 12345
    update.effective_user.full_name = "Test User"
    update.message = AsyncMock()
    update.message.text = ""
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_telegram_context():
    context = MagicMock()
    context.args = []
    context.user_data = {}
    context.bot_data = {}
    return context
