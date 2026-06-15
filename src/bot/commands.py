"""
Telegram /command handlers.
"""
from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.middlewares import admin_required
from src.bot.keyboards import category_keyboard
from src.sheets.completions import completions_manager
from src.sheets.history import history_manager
from src.sheets.inventory import inventory_manager
from src.nlp.parser import parser
from src.utils.formatters import (
    format_completions_list,
    format_inventory_list,
    format_daily_report,
    format_date,
    format_datetime,
)
from src.utils.logger import get_logger
from src.utils.permissions import is_admin, list_admins

log = get_logger(__name__)


def _get_username(update: Update) -> str:
    user = update.effective_user
    if user:
        return user.full_name or user.username or str(user.id)
    return "unknown"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start"""
    name = _get_username(update)
    uid = update.effective_user.id if update.effective_user else "?"
    admin_flag = " 👑 (מנהל)" if is_admin(uid) else ""
    text = (
        f"👋 שלום {name}{admin_flag}!\n\n"
        "אני הבוט של המטבח 🍳\n\n"
        "**איך להשתמש:**\n"
        "• שלח שם מוצר להוספה: `חלב 2`\n"
        "• סיים רכישה: `קניתי חלב`\n"
        "• בטל: `לא צריך חלב`\n"
        "• הצג רשימה: /רשימה\n"
        "• עזרה מלאה: /עזרה"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /עזרה or /help"""
    uid = update.effective_user.id if update.effective_user else 0
    admin_section = ""
    if is_admin(uid):
        admin_section = (
            "\n\n👑 *פקודות מנהל:*\n"
            "/יום_חדש – פתיחת יום חדש (ארכוב + ניקוי)\n"
            "/הוסף_מוצר [שם] – הוסף מוצר למלאי קבוע\n"
            "/השבת [שם] – השבת מוצר מהמלאי\n"
            "/הפעל [שם] – הפעל מוצר מושבת\n"
            "/דוח – סיכום יומי\n"
        )

    text = (
        "📖 *עזרה – בוט המטבח*\n\n"
        "*הוספת חוסרים:*\n"
        "`חלב` / `חלב 2` / `צריך חלב` / `חסר מוצרלה 3`\n\n"
        "*סימון כנקנה:*\n"
        "`קניתי חלב` / `הגיע חלב` / `הושלם בזיליקום`\n\n"
        "*ביטול:*\n"
        "`לא צריך חלב` / `בטל גבינה` / `הסר עגבניות`\n\n"
        "*שחזור:*\n"
        "`החזר חלב` / `תשחזר מוצרלה`\n\n"
        "*פקודות:*\n"
        "/רשימה – השלמות פעילות\n"
        "/מלאי – מלאי קבוע\n"
        "/חפש [מוצר] – חיפוש מוצר\n"
        "/דוח – סיכום יומי"
        f"{admin_section}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /רשימה"""
    try:
        items = completions_manager.get_active()
        text = format_completions_list(items)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_list error: {e}")
        await update.message.reply_text("❌ שגיאה בטעינת הרשימה. נסה שוב.")


async def cmd_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /מלאי"""
    try:
        items = inventory_manager.get_all_active()
        text = format_inventory_list(items)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_inventory error: {e}")
        await update.message.reply_text("❌ שגיאה בטעינת המלאי.")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /חפש [שם מוצר]"""
    if not context.args:
        await update.message.reply_text("🔍 שימוש: /חפש שם_מוצר")
        return

    query = " ".join(context.args)
    try:
        inv = inventory_manager.get_product(query)
        comp = completions_manager.find_item(query)
        last = history_manager.get_last_update(query)

        lines = [f"🔍 *חיפוש: {query}*\n"]

        if inv:
            active_str = "✅ פעיל" if str(inv.get("פעיל", "TRUE")).upper() != "FALSE" else "🚫 מושבת"
            lines.append(f"📦 *מלאי קבוע:* {active_str}")
            lines.append(f"  קטגוריה: {inv.get('קטגוריה', '-')}")
            lines.append(f"  כמות יעד: {inv.get('כמות יעד', '-')} {inv.get('יחידת מידה', '')}")
        else:
            lines.append("📦 *מלאי קבוע:* לא נמצא")

        if comp:
            status = comp.get("סטטוס", "-")
            qty = comp.get("כמות חסרה", "-")
            unit = comp.get("יחידת מידה", "")
            lines.append(f"\n📋 *השלמות היום:* {status}")
            lines.append(f"  כמות: {qty} {unit}")
        else:
            lines.append("\n📋 *השלמות היום:* לא ברשימה")

        if last:
            lines.append(f"\n🕐 *עדכון אחרון:*")
            lines.append(f"  {last.get('תאריך', '')} {last.get('שעה', '')} – {last.get('פעולה', '')}")
            lines.append(f"  על ידי: {last.get('מי ביצע', '-')}")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_search error: {e}")
        await update.message.reply_text("❌ שגיאה בחיפוש.")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /דוח"""
    try:
        stats = completions_manager.get_daily_stats()
        text = format_daily_report(stats)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_report error: {e}")
        await update.message.reply_text("❌ שגיאה בהפקת הדוח.")


@admin_required
async def cmd_new_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /יום_חדש – admin only"""
    actor = _get_username(update)
    today = format_date()
    archive_title = f"ארכיון {today}"

    await update.message.reply_text(f"🔄 מתחיל יום חדש... ארכוב נתוני {today}")

    try:
        stats = completions_manager.get_daily_stats()
        count = completions_manager.archive_and_clear(archive_title)

        history_manager.log_action(
            action="פתיחת יום חדש",
            product_name="",
            actor=actor,
            original_message=f"/יום_חדש",
            details=f"ארכוב {count} פריטים -> {archive_title}",
        )

        # Refresh product name cache
        names = inventory_manager.get_all_product_names()
        parser.update_product_names(names)

        report = format_daily_report(stats)
        await update.message.reply_text(
            f"✅ *יום חדש נפתח בהצלחה!*\n\n"
            f"הנתונים הועברו ל: *{archive_title}*\n\n"
            f"{report}",
            parse_mode="Markdown"
        )
    except Exception as e:
        log.error(f"cmd_new_day error: {e}")
        await update.message.reply_text("❌ שגיאה בפתיחת יום חדש.")


@admin_required
async def cmd_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /הוסף_מוצר [שם מוצר]"""
    if not context.args:
        await update.message.reply_text("שימוש: /הוסף_מוצר שם_מוצר [כמות_יעד] [יחידה]")
        return

    name = context.args[0]
    target = context.args[1] if len(context.args) > 1 else ""
    unit = context.args[2] if len(context.args) > 2 else ""

    # Show category picker
    await update.message.reply_text(
        f"📦 מוסיף *{name}* למלאי קבוע.\nבחר קטגוריה:",
        reply_markup=category_keyboard(f"{name}|{target}|{unit}"),
        parse_mode="Markdown"
    )


@admin_required
async def cmd_disable_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /השבת [שם מוצר]"""
    if not context.args:
        await update.message.reply_text("שימוש: /השבת שם_מוצר")
        return
    name = " ".join(context.args)
    actor = _get_username(update)
    ok = inventory_manager.disable_product(name)
    if ok:
        history_manager.log_action("השבתת מוצר", name, actor)
        parser.update_product_names(inventory_manager.get_all_product_names())
        await update.message.reply_text(f"🚫 *{name}* הושבת מהמלאי הקבוע.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ לא נמצא מוצר בשם *{name}*.", parse_mode="Markdown")


@admin_required
async def cmd_enable_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /הפעל [שם מוצר]"""
    if not context.args:
        await update.message.reply_text("שימוש: /הפעל שם_מוצר")
        return
    name = " ".join(context.args)
    actor = _get_username(update)
    ok = inventory_manager.enable_product(name)
    if ok:
        history_manager.log_action("הפעלת מוצר", name, actor)
        parser.update_product_names(inventory_manager.get_all_product_names())
        await update.message.reply_text(f"✅ *{name}* הופעל מחדש.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ לא נמצא מוצר בשם *{name}*.", parse_mode="Markdown")
