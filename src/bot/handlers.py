"""
Main message handler: parses free text and routes to the right action.
Supports multi-line messages and evening count (ספירת ערב).
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.keyboards import confirm_fuzzy_keyboard, new_product_keyboard, status_keyboard
from src.bot.middlewares import rate_limited
from src.nlp.intents import Intent
from src.nlp.parser import parser, ParsedMessage
from src.sheets.completions import completions_manager
from src.sheets.evening_count import evening_manager
from src.sheets.history import history_manager
from src.sheets.inventory import inventory_manager
from src.utils.logger import get_logger

log = get_logger(__name__)

CONFIRM_THRESHOLD = 0.85

# Words to ignore completely
IGNORE_WORDS = {
    "היי", "הי", "שלום", "בוקר טוב", "ערב טוב", "תודה", "אוקי", "אוקיי",
    "כן", "לא", "בסדר", "טוב", "נהדר", "מעולה", "ok", "yes", "no", "hi", "hello"
}


def _get_username(update: Update) -> str:
    user = update.effective_user
    if user:
        return user.full_name or user.username or str(user.id)
    return "unknown"


def _should_ignore(text: str) -> bool:
    return text.strip().lower() in IGNORE_WORDS


@rate_limited
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    actor = _get_username(update)

    if _should_ignore(text):
        return

    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    if len(lines) > 1:
        await _handle_multi_line(update, context, lines, actor)
        return

    parsed = parser.parse(text)
    if parsed is None:
        return

    if parsed.suggestion and parsed.confidence < CONFIRM_THRESHOLD:
        context.user_data["pending_message"] = {
            "parsed": parsed, "actor": actor, "original": text,
        }
        await update.message.reply_text(
            f"התכוונת ל-{parsed.suggestion}?",
            reply_markup=confirm_fuzzy_keyboard(parsed.suggestion, text),
        )
        return

    await _process_parsed(update, context, parsed, actor)


async def _handle_multi_line(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    lines: list[str],
    actor: str,
) -> None:
    results = []
    needs_confirm = []

    for line in lines:
        if _should_ignore(line):
            continue

        parsed = parser.parse(line)
        if parsed is None:
            continue

        # Fuzzy match needs confirmation - collect for later
        if parsed.suggestion and parsed.confidence < CONFIRM_THRESHOLD:
            needs_confirm.append((line, parsed.suggestion))
            continue

        if parsed.intent == Intent.COUNT:
            result = evening_manager.update_count(
                parsed.product_name, parsed.quantity, actor,
                unit=parsed.unit or ""
            )
            history_manager.log_action("ספירת ערב", parsed.product_name, actor, line, str(parsed.quantity))
            results.append(f"✅ נשאר {parsed.product_name} – {parsed.quantity}")

        elif parsed.intent == Intent.ADD:
            inv_product = inventory_manager.get_product(parsed.product_name)
            if inv_product:
                result = completions_manager.add_or_update(
                    name=parsed.product_name, qty=parsed.quantity, reporter=actor,
                )
                unit_str = parsed.unit or result.get("unit", "")
                if result["action"] == "added":
                    results.append(f"✅ {parsed.product_name} – {parsed.quantity} {unit_str}".strip())
                else:
                    results.append(f"🔄 {parsed.product_name} – {result.get('old_qty')} → {result.get('new_qty')} {unit_str}".strip())
                history_manager.log_action("הוספת חוסר", parsed.product_name, actor, line, str(parsed.quantity))
            else:
                inventory_manager.add_product(parsed.product_name)
                completions_manager.add_or_update(parsed.product_name, parsed.quantity, actor)
                history_manager.log_action("הוספת מוצר חדש", parsed.product_name, actor, line, str(parsed.quantity))
                parser.update_product_names(inventory_manager.get_all_product_names())
                results.append(f"➕ {parsed.product_name} – {parsed.quantity} (חדש)")

    msg = ""
    if results:
        msg += f"עודכנו {len(results)} פריטים:\n\n" + "\n".join(results)

    if needs_confirm:
        msg += "\n\nנדרש אישור:\n"
        for original, suggestion in needs_confirm:
            msg += f"• {original} → התכוונת ל-{suggestion}?\n"

    if msg:
        await update.message.reply_text(msg)


async def _process_parsed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    parsed: ParsedMessage,
    actor: str,
) -> None:
    name = parsed.product_name
    qty = parsed.quantity
    unit = parsed.unit
    original = parsed.original_text

    if parsed.intent == Intent.COUNT:
        await _handle_count(update, context, name, qty, unit, actor, original)
    elif parsed.intent == Intent.ADD:
        await _handle_add(update, context, name, qty, unit, actor, original)
    elif parsed.intent == Intent.MARK_DONE:
        await _handle_done(update, context, name, actor, original)
    elif parsed.intent == Intent.CANCEL:
        await _handle_cancel(update, context, name, actor, original)
    elif parsed.intent == Intent.RESTORE:
        await _handle_restore(update, context, name, actor, original)


async def _handle_count(update, context, name, qty, unit, actor, original) -> None:
    """Handle evening count - worker reports what's left."""
    result = evening_manager.update_count(name, qty, actor, unit or "")
    history_manager.log_action("ספירת ערב", name, actor, original, str(qty), unit or "")

    action = "עודכן" if result["action"] == "updated" else "נרשם"
    await update.message.reply_text(
        f"✅ {action}: נשאר {name} – {qty} {unit or ''}".strip()
    )


async def _handle_add(update, context, name, qty, unit, actor, original) -> None:
    inv_product = inventory_manager.get_product(name)
    if inv_product is None:
        context.user_data["pending_add"] = {
            "name": name, "qty": qty, "unit": unit, "actor": actor, "original": original
        }
        await update.message.reply_text(
            f"? {name} לא נמצא במלאי הקבוע.\nמה לעשות?",
            reply_markup=new_product_keyboard(name),
        )
        return

    result = completions_manager.add_or_update(name=name, qty=qty, reporter=actor)
    history_manager.log_action(
        action="הוספת חוסר" if result["action"] == "added" else "עדכון כמות",
        product_name=name, actor=actor, original_message=original,
        qty=str(qty), unit=unit or result.get("unit", ""),
    )
    unit_str = unit or result.get("unit", "")
    if result["action"] == "added":
        await update.message.reply_text(
            f"נוסף: {name} – {qty} {unit_str}".strip(),
            reply_markup=status_keyboard(name),
        )
    else:
        await update.message.reply_text(
            f"עודכן: {name}\n{result.get('old_qty')} → {result.get('new_qty')} {unit_str}".strip(),
        )


async def _handle_done(update, context, name, actor, original) -> None:
    ok = completions_manager.set_status(name, "נקנה", actor)
    if ok:
        history_manager.log_action("סימון כנקנה", name, actor, original)
        await update.message.reply_text(f"{name} סומן כנקנה ✅")
    else:
        await update.message.reply_text(f"{name} לא נמצא ברשימה הפעילה.")


async def _handle_cancel(update, context, name, actor, original) -> None:
    ok = completions_manager.set_status(name, "בוטל", actor)
    if ok:
        history_manager.log_action("ביטול פריט", name, actor, original)
        await update.message.reply_text(f"{name} בוטל.")
    else:
        await update.message.reply_text(f"{name} לא נמצא ברשימה.")


async def _handle_restore(update, context, name, actor, original) -> None:
    ok = completions_manager.restore_cancelled(name)
    if ok:
        history_manager.log_action("שחזור פריט", name, actor, original)
        await update.message.reply_text(f"{name} הוחזר לרשימה.")
    else:
        await update.message.reply_text(f"לא נמצא פריט מבוטל בשם {name}.")


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    actor = _get_username(update)

    if data.startswith("confirm_fuzzy:"):
        canonical = data.split(":", 1)[1]
        pending = context.user_data.pop("pending_message", None)
        if pending:
            parsed: ParsedMessage = pending["parsed"]
            parsed.product_name = canonical
            parsed.suggestion = None
            await _process_parsed(update, context, parsed, pending["actor"])
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.edit_message_text("הפעולה פגה. שלח שוב.")

    elif data == "cancel_fuzzy":
        context.user_data.pop("pending_message", None)
        context.user_data.pop("pending_add", None)
        await query.edit_message_text("בוטל.")

    elif data.startswith("add_new_product:"):
        name = data.split(":", 1)[1]
        pending = context.user_data.pop("pending_add", None)
        qty = pending["qty"] if pending else 1
        unit = pending["unit"] if pending else ""
        original = pending["original"] if pending else ""
        inventory_manager.add_product(name)
        completions_manager.add_or_update(name, qty, actor)
        history_manager.log_action("הוספת מוצר חדש", name, actor, original, str(qty), unit or "")
        parser.update_product_names(inventory_manager.get_all_product_names())
        await query.edit_message_text(f"{name} נוסף למלאי הקבוע ולרשימת היום!")

    elif data.startswith("add_temp:"):
        name = data.split(":", 1)[1]
        pending = context.user_data.pop("pending_add", None)
        qty = pending["qty"] if pending else 1
        unit = pending["unit"] if pending else ""
        original = pending["original"] if pending else ""
        completions_manager.add_or_update(name, qty, actor)
        history_manager.log_action("הוספת חוסר זמני", name, actor, original, str(qty), unit or "")
        await query.edit_message_text(f"{name} נוסף לרשימת היום.")

    elif data.startswith("set_category:"):
        _, packed_name, category = data.split(":", 2)
        parts = packed_name.split("|")
        name = parts[0]
        target = parts[1] if len(parts) > 1 else ""
        unit = parts[2] if len(parts) > 2 else ""
        inventory_manager.add_product(name, category=category, target_qty=target, unit=unit)
        history_manager.log_action("הוספת מוצר למלאי", name, actor, details=f"קטגוריה: {category}")
        parser.update_product_names(inventory_manager.get_all_product_names())
        await query.edit_message_text(f"{name} נוסף למלאי בקטגוריה {category}.")

    elif data.startswith("status:"):
        _, status, name = data.split(":", 2)
        ok = completions_manager.set_status(name, status, actor)
        if ok:
            history_manager.log_action(f"עדכון סטטוס -> {status}", name, actor)
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"סטטוס {name} עודכן ל-{status}")
        else:
            await query.answer(f"לא נמצא: {name}", show_alert=True)
