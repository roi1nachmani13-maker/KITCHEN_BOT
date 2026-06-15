"""
Kitchen Bot - main entry point.
"""
from __future__ import annotations

import sys
from datetime import time as dtime

import pytz
from telegram import BotCommand
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot.commands import (
    cmd_start,
    cmd_help,
    cmd_list,
    cmd_inventory,
    cmd_search,
    cmd_report,
    cmd_new_day,
    cmd_add_product,
    cmd_disable_product,
    cmd_enable_product,
)
from src.bot.handlers import handle_message, handle_callback
from src.nlp.parser import parser
from src.sheets.client import sheets_client
from src.sheets.completions import completions_manager
from src.sheets.inventory import inventory_manager
from src.utils.config import config
from src.utils.formatters import format_daily_report, format_date
from src.utils.logger import get_logger

log = get_logger("main")


async def _scheduled_daily_summary(context) -> None:
    try:
        stats = completions_manager.get_daily_stats()
        text = f"סיכום יומי - {format_date()}\n\n" + format_daily_report(stats)
        for chat_id in context.bot_data.get("group_chat_ids", set()):
            await context.bot.send_message(chat_id, text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"Daily summary error: {e}")


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
        BotCommand("newday", "פתח יום חדש (מנהל)"),
        BotCommand("addproduct", "הוסף מוצר למלאי (מנהל)"),
        BotCommand("disable", "השבת מוצר (מנהל)"),
        BotCommand("enable", "הפעל מוצר (מנהל)"),
        BotCommand("help", "עזרה"),
        BotCommand("start", "התחל"),
    ])
    log.info("Bot commands registered")


def build_application() -> Application:
    config.validate()
    tz = pytz.timezone(config.timezone)

    app = (
        Application.builder()
        .token(config.telegram_bot_token)
        .post_init(post_init)
        .build()
    )

    # Commands
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

    # Callbacks and messages
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Scheduled jobs
    if config.daily_summary_enabled:
        summary_time = dtime(
            hour=config.daily_summary_hour,
            minute=config.daily_summary_minute,
            tzinfo=tz,
        )
        app.job_queue.run_daily(_scheduled_daily_summary, time=summary_time)

    return app


def main() -> None:
    log.info("Starting Kitchen Bot...")
    app = build_application()
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    main()
