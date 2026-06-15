"""Kitchen Bot - main entry point."""
from __future__ import annotations

from telegram import BotCommand
from telegram.ext import (
    Application, CallbackQueryHandler,
    CommandHandler, MessageHandler, filters,
)

from src.bot.commands import (
    cmd_start, cmd_help, cmd_list, cmd_inventory,
    cmd_search, cmd_report, cmd_new_day,
    cmd_add_product, cmd_disable_product, cmd_enable_product,
)
from src.bot.handlers import handle_message, handle_callback
from src.nlp.parser import parser
from src.sheets.client import sheets_client
from src.sheets.inventory import inventory_manager
from src.utils.config import config
from src.utils.logger import get_logger

log = get_logger("main")


async def post_init(application: Application) -> None:
    log.info("Connecting to Google Sheets...")
    sheets_client.connect()
    names = inventory_manager.get_all_product_names()
    parser.update_product_names(names)
    log.info(f"Loaded {len(names)} products into NLP parser")
    await application.bot.set_my_commands([
        BotCommand("list", "השלמות פעילות להיום"),
        BotCommand("inventory", "מלאי קבוע"),
        BotCommand("search", "חפש מוצר"),
        BotCommand("report", "סיכום יומי"),
        BotCommand("newday", "פתח יום חדש - מנהל"),
        BotCommand("addproduct", "הוסף מוצר למלאי - מנהל"),
        BotCommand("disable", "השבת מוצר - מנהל"),
        BotCommand("enable", "הפעל מוצר - מנהל"),
        BotCommand("help", "עזרה"),
        BotCommand("start", "התחל"),
    ])
    log.info("Bot ready")


def build_application() -> Application:
    config.validate()
    app = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("inventory", cmd_inventory))
    app.add_handler(CommandHandler("search", cmd_search))
    app.add_handler(CommandHandler("report", cmd_report))
    app.add_handler(CommandHandler("newday", cmd_new_day))
    app.add_handler(CommandHandler("addproduct", cmd_add_product))
    app.add_handler(CommandHandler("disable", cmd_disable_product))
    app.add_handler(CommandHandler("enable", cmd_enable_product))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    return app


def main() -> None:
    log.info("Starting Kitchen Bot...")
    build_application().run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    main()
