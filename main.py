"""
Kitchen Bot – main entry point.
Sets up the Telegram application, registers handlers, and starts polling.
"""
from __future__ import annotations

import asyncio
import signal
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
    """Send daily summary to all groups the bot is in."""
    try:
        stats = completions_manager.get_daily_stats()
        text = (
            f"📊 *סיכום יומי אוטומטי – {format_date()}*\n\n"
            + format_daily_report(stats)
        )
        # Send to all groups where we have a chat_id stored
        for chat_id in context.bot_data.get("group_chat_ids", set()):
            await context.bot.send_message(chat_id, text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"Daily summary error: {e}")


async def post_init(application: Application) -> None:
    """Run after the bot starts."""
    # Connect to Google Sheets
    log.info("Connecting to Google Sheets...")
    sheets_client.connect()

    # Load product names into NLP parser
    names = inventory_manager.get_all_product_names()
    parser.update_product_names(names)
    log.info(f"Loaded {len(names)} products into NLP parser")

    # Register bot commands in Telegram UI
    await application.bot.set_my_commands([
        BotCommand("רשימה", "השלמות פעילות להיום"),
        BotCommand("מלאי", "מלאי קבוע של המטבח"),
        BotCommand("חפש", "חפש מוצר"),
        BotCommand("דוח", "סיכום יומי"),
        BotCommand("יום_חדש", "פתח יום חדש (מנהל)"),
        BotCommand("הוסף_מוצר", "הוסף מוצר למלאי (מנהל)"),
        BotCommand("השבת", "השבת מוצר (מנהל)"),
        BotCommand("הפעל", "הפעל מוצר (מנהל)"),
        BotCommand("עזרה", "הצג עזרה"),
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

    # ---- Command handlers ----
    app.add_handler(CommandHandler(["start"], cmd_start))
    app.add_handler(CommandHandler(["עזרה", "help"], cmd_help))
    app.add_handler(CommandHandler(["רשימה", "list"], cmd_list))
    app.add_handler(CommandHandler(["מלאי", "inventory"], cmd_inventory))
    app.add_handler(CommandHandler(["חפש", "search"], cmd_search))
    app.add_handler(CommandHandler(["דוח", "report"], cmd_report))
    app.add_handler(CommandHandler(["יום_חדש", "newday"], cmd_new_day))
    app.add_handler(CommandHandler(["הוסף_מוצר", "add_product"], cmd_add_product))
    app.add_handler(CommandHandler(["השבת", "disable"], cmd_disable_product))
    app.add_handler(CommandHandler(["הפעל", "enable"], cmd_enable_product))

    # ---- Callback queries (inline keyboards) ----
    app.add_handler(CallbackQueryHandler(handle_callback))

    # ---- Free text messages ----
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # ---- Scheduled jobs ----
    job_queue = app.job_queue

    if config.daily_summary_enabled:
        summary_time = dtime(
            hour=config.daily_summary_hour,
            minute=config.daily_summary_minute,
            tzinfo=tz,
        )
        job_queue.run_daily(_scheduled_daily_summary, time=summary_time, name="daily_summary")
        log.info(f"Daily summary scheduled at {summary_time}")

    return app


def main() -> None:
    log.info("Starting Kitchen Bot...")
    app = build_application()

    # Graceful shutdown
    def _stop(sig, frame):
        log.info("Shutting down...")
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=["message", "callback_query"],
    )


if __name__ == "__main__":
    main()
