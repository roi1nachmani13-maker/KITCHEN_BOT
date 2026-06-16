"""
Main message handler: parses free text and routes to the right action.
Also handles callback queries from inline keyboards.
Supports multi-line messages (one product per line).
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from src.bot.keyboards import confirm_fuzzy_keyboard, new_product_keyboard, status_keyboard
from src.bot.middlewares import rate_limited
from src.nlp.intents import Intent
from src.nlp.parser import parser, ParsedMessage
from src.sheets.completions import completions_manager
from src.sheets.history import history_manager
from src.sheets.inventory import inventory_manager
from src.utils.logger import get_logger

log = get_logger(__name__)

CONFIRM_THRESHOLD = 0.85


def _get_username(update: Update) -> str:
    user = update.effective_user
    if user:
        return user.full_name or user.username or str(user.id)
    return "unknown"


@rate_limited
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    actor = _get_username(update)

    # Multi-line support: split by newline and process each line
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]

    if len(lines) > 1:
        await _handle_multi_line(update, context, lines, actor)
        return

    # Single line
    parsed = parser.parse(text)
    if parsed is None:
        return

    if parsed.suggestion and parsed.confidence < CONFIRM_THRESHOLD:
        context.user_data["pending_message"] = {
            "parsed": parsed,
            "actor": actor,
            "original": text,
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
    skipped = []

    for line in lines:
        parsed = parser.parse(line)
        if parsed is None:
            skipped.append(line)
            continue

        if parsed.intent == Intent.ADD:
            inv_product = inventory_manager.get_product(parsed.product_name)
            unit = parsed.unit or ""
            if inv_product:
                result = completions_manager.add_or_update(
                    name=parsed.product_name,
                    qty=parsed.quantity,
                    reporter=actor,
                )
                history_manager.log_action(
                    action="הוספת חוסר" if result["action"] == "added" else "עדכון כמות",
                    product_name=parsed.product_name,
                    actor=actor,
                    original_message=line,
                    qty=str(parsed.quantity),
                    unit=unit or result.get("unit", ""),
                )
                unit_str = unit or result.get("unit", "")
                if result["action"] == "added":
                    results.append(f"✅ {parsed.product_name} – {parsed.quantity} {unit_str}".strip())
                else:
                    results.append(f"🔄 {parsed.product_name} – {result.get('old_qty')} → {result.get('new_qty')} {unit_str}".strip())
            else:
                # Add to inventory automatically and then to completions
                inventory_manager.add_product(parsed.product_name)
                completions_manager.add_or_update(
                    name=parsed.product_name,
                    qty=parsed.quantity,
                    reporter=actor,
                )
                history_manager.log_action("הוספת מוצר חדש", parsed.product_name, actor, line, str(parsed.quantity), unit)
                parser.update_product_names(inventory_manager.get_all_product_names())
                results.append(f"➕ {parsed.product_name} – {parsed.quantity} {unit}".strip() + " (חדש)")
        else:
            await _process_parsed(update, context, parsed, actor)

    if results:
        summary = "\n".join(results)
        if skipped:
            summary += f"\n\nדולג: {', '.join(skipped)}"
        await update.message.reply_text(f"נוספו {len(results)} פריטים:\n\n{summary}")


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

    if parsed.intent == Intent.ADD:
        await _handle_add(update, context, name, qty, unit, actor, original)
    elif parsed.intent == Intent.MARK_DONE:
        await _handle_done(update, context, name, actor, original)
    elif parsed.intent == Intent.CANCEL:
        await _handle_cancel(update, context, name, actor, original)
    elif parsed.intent == Intent.RESTORE:
        await _handle_restore(update, context, name, actor, original)


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

    result = completions_manager.add_or_update(
        name=name, qty=qty, reporter=actor,
        notes=f"יחידה: {unit}" if unit else "",
    )
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
        old = result.get("old_qty", 0)
        new = result.get("new_qty", qty)
        await update.message.reply_text(
            f"עודכן: {name}\n{old} -> {new} {unit_str}".strip(),
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
