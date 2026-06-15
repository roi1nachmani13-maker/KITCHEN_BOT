"""
Telegram /command handlers.
"""
from __future__ import annotations

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
)
from src.utils.logger import get_logger
from src.utils.permissions import is_admin

log = get_logger(__name__)


def _get_username(update: Update) -> str:
    user = update.effective_user
    if user:
        return user.full_name or user.username or str(user.id)
    return "unknown"


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    name = _get_username(update)
    uid = update.effective_user.id if update.effective_user else "?"
    admin_flag = " (מנהל)" if is_admin(uid) else ""
    text = (
        f"שלום {name}{admin_flag}!\n\n"
        "אני הבוט של המטבח\n\n"
        "איך להשתמש:\n"
        "שלח שם מוצר להוספה: חלב 2\n"
        "סיים רכישה: קניתי חלב\n"
        "בטל: לא צריך חלב\n"
        "הצג רשימה: /list\n"
        "עזרה מלאה: /help"
    )
    await update.message.reply_text(text)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    uid = update.effective_user.id if update.effective_user else 0
    admin_section = ""
    if is_admin(uid):
        admin_section = (
            "\n\nפקודות מנהל:\n"
            "/newday - פתיחת יום חדש\n"
            "/addproduct [שם] - הוסף מוצר למלאי\n"
            "/disable [שם] - השבת מוצר\n"
            "/enable [שם] - הפעל מוצר\n"
            "/report - סיכום יומי"
        )
    text = (
        "עזרה - בוט המטבח\n\n"
        "הוספת חוסרים:\n"
        "חלב / חלב 2 / צריך חלב / חסר מוצרלה 3\n\n"
        "סימון כנקנה:\n"
        "קניתי חלב / הגיע חלב / הושלם בזיליקום\n\n"
        "ביטול:\n"
        "לא צריך חלב / בטל גבינה\n\n"
        "שחזור:\n"
        "החזר חלב / תשחזר מוצרלה\n\n"
        "פקודות:\n"
        "/list - השלמות פעילות\n"
        "/inventory - מלאי קבוע\n"
        "/search [מוצר] - חיפוש\n"
        "/report - סיכום יומי"
        f"{admin_section}"
    )
    await update.message.reply_text(text)


async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        items = completions_manager.get_active()
        text = format_completions_list(items)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_list error: {e}")
        await update.message.reply_text("שגיאה בטעינת הרשימה. נסה שוב.")


async def cmd_inventory(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        items = inventory_manager.get_all_active()
        text = format_inventory_list(items)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_inventory error: {e}")
        await update.message.reply_text("שגיאה בטעינת המלאי.")


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("שימוש: /search שם_מוצר")
        return
    query = " ".join(context.args)
    try:
        inv = inventory_manager.get_product(query)
        comp = completions_manager.find_item(query)
        last = history_manager.get_last_update(query)
        lines = [f"חיפוש: {query}\n"]
        if inv:
            active_str = "פעיל" if str(inv.get("פעיל", "TRUE")).upper() != "FALSE" else "מושבת"
            lines.append(f"מלאי קבוע: {active_str}")
            lines.append(f"קטגוריה: {inv.get('קטגוריה', '-')}")
            lines.append(f"כמות יעד: {inv.get('כמות יעד', '-')} {inv.get('יחידת מידה', '')}")
        else:
            lines.append("מלאי קבוע: לא נמצא")
        if comp:
            lines.append(f"\nהשלמות היום: {comp.get('סטטוס', '-')}")
            lines.append(f"כמות: {comp.get('כמות חסרה', '-')} {comp.get('יחידת מידה', '')}")
        else:
            lines.append("\nהשלמות היום: לא ברשימה")
        if last:
            lines.append(f"\nעדכון אחרון: {last.get('תאריך', '')} {last.get('שעה', '')}")
            lines.append(f"על ידי: {last.get('מי ביצע', '-')}")
        await update.message.reply_text("\n".join(lines))
    except Exception as e:
        log.error(f"cmd_search error: {e}")
        await update.message.reply_text("שגיאה בחיפוש.")


async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        stats = completions_manager.get_daily_stats()
        text = format_daily_report(stats)
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        log.error(f"cmd_report error: {e}")
        await update.message.reply_text("שגיאה בהפקת הדוח.")


@admin_required
async def cmd_new_day(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    actor = _get_username(update)
    today = format_date()
    archive_title = f"archive {today}"
    await update.message.reply_text(f"מתחיל יום חדש... ארכוב נתוני {today}")
    try:
        stats = completions_manager.get_daily_stats()
        count = completions_manager.archive_and_clear(archive_title)
        history_manager.log_action(
            action="פתיחת יום חדש",
            product_name="",
            actor=actor,
            original_message="/newday",
            details=f"ארכוב {count} פריטים",
        )
        names = inventory_manager.get_all_product_names()
        parser.update_product_names(names)
        report = format_daily_report(stats)
        await update.message.reply_text(
            f"יום חדש נפתח!\nהנתונים הועברו ל: {archive_title}\n\n{report}"
        )
    except Exception as e:
        log.error(f"cmd_new_day error: {e}")
        await update.message.reply_text("שגיאה בפתיחת יום חדש.")


@admin_required
async def cmd_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("שימוש: /addproduct שם_מוצר [כמות_יעד] [יחידה]")
        return
    name = context.args[0]
    target = context.args[1] if len(context.args) > 1 else ""
    unit = context.args[2] if len(context.args) > 2 else ""
    await update.message.reply_text(
        f"מוסיף {name} למלאי קבוע.\nבחר קטגוריה:",
        reply_markup=category_keyboard(f"{name}|{target}|{unit}"),
    )


@admin_required
async def cmd_disable_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("שימוש: /disable שם_מוצר")
        return
    name = " ".join(context.args)
    actor = _get_username(update)
    ok = inventory_manager.disable_product(name)
    if ok:
        history_manager.log_action("השבתת מוצר", name, actor)
        parser.update_product_names(inventory_manager.get_all_product_names())
        await update.message.reply_text(f"{name} הושבת מהמלאי.")
    else:
        await update.message.reply_text(f"לא נמצא מוצר בשם {name}.")


@admin_required
async def cmd_enable_product(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("שימוש: /enable שם_מוצר")
        return
    name = " ".join(context.args)
    actor = _get_username(update)
    ok = inventory_manager.enable_product(name)
    if ok:
        history_manager.log_action("הפעלת מוצר", name, actor)
        parser.update_product_names(inventory_manager.get_all_product_names())
        await update.message.reply_text(f"{name} הופעל מחדש.")
    else:
        await update.message.reply_text(f"לא נמצא מוצר בשם {name}.")
