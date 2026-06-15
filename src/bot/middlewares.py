"""
Bot middleware: rate limiting, error handling, logging.
"""
from __future__ import annotations

import functools
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Any

from telegram import Update
from telegram.ext import ContextTypes

from src.utils.logger import get_logger

log = get_logger(__name__)

# Simple in-memory rate limiting: max N messages per minute per user
_RATE_LIMIT_COUNT = 20
_RATE_LIMIT_WINDOW = 60  # seconds
_user_message_times: Dict[int, list] = defaultdict(list)


def rate_limited(func: Callable) -> Callable:
    """Decorator: reject if user sends too many messages."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else 0
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=_RATE_LIMIT_WINDOW)

        # Clean old entries
        _user_message_times[user_id] = [
            t for t in _user_message_times[user_id] if t > window_start
        ]

        if len(_user_message_times[user_id]) >= _RATE_LIMIT_COUNT:
            await update.message.reply_text("⚠️ יותר מדי הודעות. אנא המתן רגע.")
            return

        _user_message_times[user_id].append(now)
        return await func(update, context, *args, **kwargs)

    return wrapper


def admin_required(func: Callable) -> Callable:
    """Decorator: allow only admins."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from src.utils.permissions import is_admin
        user_id = update.effective_user.id if update.effective_user else 0
        if not is_admin(user_id):
            await update.message.reply_text("🔒 פקודה זו מיועדת למנהלים בלבד.")
            return
        return await func(update, context, *args, **kwargs)

    return wrapper
