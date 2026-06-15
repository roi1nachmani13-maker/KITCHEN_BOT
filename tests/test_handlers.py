"""
Integration-style tests for bot message handlers.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.handlers import handle_message
from src.nlp.parser import MessageParser


@pytest.fixture
def parser_with_products():
    return MessageParser(product_names=["חלב", "עגבניות", "מוצרלה"])


@pytest.fixture
def update_factory():
    def _make(text: str, user_id: int = 12345, username: str = "Test User"):
        update = MagicMock()
        update.effective_user.id = user_id
        update.effective_user.full_name = username
        update.message = AsyncMock()
        update.message.text = text
        update.message.reply_text = AsyncMock()
        return update
    return _make


@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.user_data = {}
    ctx.bot_data = {}
    return ctx


class TestHandleMessage:
    @pytest.mark.asyncio
    async def test_add_product_known(self, update_factory, context):
        update = update_factory("חלב 2")
        with (
            patch("src.bot.handlers.parser") as mock_parser,
            patch("src.bot.handlers.inventory_manager") as mock_inv,
            patch("src.bot.handlers.completions_manager") as mock_comp,
            patch("src.bot.handlers.history_manager"),
        ):
            from src.nlp.intents import Intent
            from src.nlp.parser import ParsedMessage

            mock_parser.parse.return_value = ParsedMessage(
                intent=Intent.ADD,
                product_name="חלב",
                quantity=2.0,
                original_text="חלב 2",
                confidence=1.0,
            )
            mock_inv.get_product.return_value = {
                "שם מוצר": "חלב", "יחידת מידה": "ליטר", "קטגוריה": "חלב"
            }
            mock_comp.add_or_update.return_value = {
                "action": "added", "name": "חלב", "qty": 2.0, "unit": "ליטר"
            }

            await handle_message(update, context)

        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "חלב" in call_args

    @pytest.mark.asyncio
    async def test_command_ignored(self, update_factory, context):
        update = update_factory("/רשימה")
        with patch("src.bot.handlers.parser") as mock_parser:
            mock_parser.parse.return_value = None
            await handle_message(update, context)
        update.message.reply_text.assert_not_called()

    @pytest.mark.asyncio
    async def test_fuzzy_match_shows_confirmation(self, update_factory, context):
        update = update_factory("חלאב")
        with patch("src.bot.handlers.parser") as mock_parser:
            from src.nlp.intents import Intent
            from src.nlp.parser import ParsedMessage

            mock_parser.parse.return_value = ParsedMessage(
                intent=Intent.ADD,
                product_name="חלב",
                quantity=1.0,
                original_text="חלאב",
                confidence=0.8,
                suggestion="חלב",
            )

            await handle_message(update, context)

        update.message.reply_text.assert_called_once()
        # Should show fuzzy confirmation keyboard
        call_kwargs = update.message.reply_text.call_args[1]
        assert "reply_markup" in call_kwargs
