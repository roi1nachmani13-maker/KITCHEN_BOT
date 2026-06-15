"""
Telegram inline keyboards for confirmation flows.
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_fuzzy_keyboard(canonical_name: str, original: str) -> InlineKeyboardMarkup:
    """Ask user to confirm fuzzy-matched product name."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"✅ כן, {canonical_name}", callback_data=f"confirm_fuzzy:{canonical_name}"),
            InlineKeyboardButton("❌ לא, ביטול", callback_data="cancel_fuzzy"),
        ]
    ])


def new_product_keyboard(name: str) -> InlineKeyboardMarkup:
    """Ask if user wants to add unknown product to inventory."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ הוסף למלאי", callback_data=f"add_new_product:{name}"),
            InlineKeyboardButton("📝 רק להיום", callback_data=f"add_temp:{name}"),
            InlineKeyboardButton("❌ ביטול", callback_data="cancel_fuzzy"),
        ]
    ])


def category_keyboard(product_name: str) -> InlineKeyboardMarkup:
    """Choose category for new product."""
    categories = ["ירקות ופירות", "בשר ודגים", "גבינות ומוצרי חלב",
                  "לחם ומאפים", "יבש ושימורים", "שתייה", "ניקיון", "כללי"]
    buttons = []
    row = []
    for i, cat in enumerate(categories):
        row.append(InlineKeyboardButton(cat, callback_data=f"set_category:{product_name}:{cat}"))
        if len(row) == 2 or i == len(categories) - 1:
            buttons.append(row)
            row = []
    return InlineKeyboardMarkup(buttons)


def status_keyboard(product_name: str) -> InlineKeyboardMarkup:
    """Quick status update buttons."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ נקנה", callback_data=f"status:נקנה:{product_name}"),
            InlineKeyboardButton("🔄 בטיפול", callback_data=f"status:בטיפול:{product_name}"),
            InlineKeyboardButton("❌ בטל", callback_data=f"status:בוטל:{product_name}"),
        ]
    ])
