"""
Main message handler: parses free text and routes to the right action.
Also handles callback queries from inline keyboards.
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

# Confidence threshold below which we ask for confirmation
CONFIRM_THRESHOLD = 0.85


def _get_username(update: Update) -> str:
    user = update.effective_user
    if user:
        return user.full_name or user.username or str(user.id)
    return "unknown"


@rate_limited
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all non-command text messages."""
    text = update.message.text or ""
    actor = _get_username(update)

    parsed = parser.parse(text)

    if parsed is None:
        return  # not an actionable message

    # If confidence is low, ask for confirmation
    if parsed.suggestion and parsed.confidence < CONFIRM_THRESHOLD:
        context.user_data["pending_message"] = {
            "parsed": parsed,
            "actor": actor,
            "original": text,
        }
        await update.message.reply_text(
            f"❓ התכוונת ל-*{parsed.suggestion}*?",
            parse_mode="Markdown",
            reply_markup=confirm_fuzzy_keyboard(parsed.suggestion, text),
        )
        return

    # Confidence is good enough – process directly
    await _process_parsed(update, context, parsed, actor)


async def _process_parsed(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    parsed: ParsedMessage,
    actor: str,
) -> None:
    """Execute the parsed intent."""
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


async def _handle_add(
    update, context, name, qty, unit, actor, original
) -> None:
    """Handle ADD intent."""
    # Check if product exists in inventory
    inv_product = inventory_manager.get_product(name)

    if inv_product is None:
        # Unknown product – ask what to do
        context.user_data["pending_add"] = {
            "name": name, "qty": qty, "unit": unit, "actor": actor, "original": original
        }
        await update.message.reply_text(
            f"❓ *{name}* לא נמצא במלאי הקבוע.\nמה לעשות?",
            parse_mode="Markdown",
            reply_markup=new_product_keyboard(name),
        )
        return

    result = completions_manager.add_or_update(
        name=name,
        qty=qty,
        reporter=actor,
        notes=f"יחידה: {unit}" if unit else "",
    )

    history_manager.log_action(
        action="הוספת חוסר" if result["action"] == "added" else "עדכון כמות",
        product_name=name,
        actor=actor,
        original_message=original,
        qty=str(qty),
        unit=unit or result.get("unit", ""),
    )

    unit_str = unit or result.get("unit", "")

    if result["action"] == "added":
        qty_str = f"{qty} {unit_str}".strip()
        await update.message.reply_text(
            f"✅ נוסף: *{name}* – {qty_str}",
            parse_mode="Markdown",
            reply_markup=status_keyboard(name),
        )
    else:
        old = result.get("old_qty", 0)
        new = result.get("new_qty", qty)
        unit_str = unit or result.get("unit", "")
        await update.message.reply_text(
            f"🔄 עודכן: *{name}*\n{old} → *{new} {unit_str}*".strip(),
            parse_mode="Markdown",
        )


async def _handle_done(update, context, name, actor, original) -> None:
    """Handle MARK_DONE intent."""
    ok = completions_manager.set_status(name, "נקנה", actor)
    if ok:
        history_manager.log_action("סימון כנקנה", name, actor, original)
        await update.message.reply_text(f"✓ *{name}* סומן כנקנה ✅", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"⚠️ *{name}* לא נמצא ברשימה הפעילה.\n"
            "אולי כבר בוטל? שלח `החזר {name}` לשחזור.".replace("{name}", name),
            parse_mode="Markdown"
        )


async def _handle_cancel(update, context, name, actor, original) -> None:
    """Handle CANCEL intent."""
    ok = completions_manager.set_status(name, "בוטל", actor)
    if ok:
        history_manager.log_action("ביטול פריט", name, actor, original)
        await update.message.reply_text(f"✗ *{name}* בוטל.", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ *{name}* לא נמצא ברשימה.", parse_mode="Markdown")


async def _handle_restore(update, context, name, actor, original) -> None:
    """Handle RESTORE intent."""
    ok = completions_manager.restore_cancelled(name)
    if ok:
        history_manager.log_action("שחזור פריט", name, actor, original)
        await update.message.reply_text(f"↩ *{name}* הוחזר לרשימה.", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"⚠️ לא נמצא פריט מבוטל בשם *{name}*.",
            parse_mode="Markdown"
        )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline keyboard callback queries."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    actor = _get_username(update)

    # ---- Fuzzy confirmation ----
    if data.startswith("confirm_fuzzy:"):
        canonical = data.split(":", 1)[1]
        pending = context.user_data.pop("pending_message", None)
        if pending:
            parsed: ParsedMessage = pending["parsed"]
            parsed.product_name = canonical
            parsed.suggestion = None
            # Re-use update object but with the original message text
            await _process_parsed(update, context, parsed, pending["actor"])
            await query.edit_message_reply_markup(reply_markup=None)
        else:
            await query.edit_message_text("⏰ הפעולה פגה. שלח שוב.")

    elif data == "cancel_fuzzy":
        context.user_data.pop("pending_message", None)
        context.user_data.pop("pending_add", None)
        await query.edit_message_text("❌ בוטל.")

    # ---- New product options ----
    elif data.startswith("add_new_product:"):
        name = data.split(":", 1)[1]
        pending = context.user_data.pop("pending_add", None)
        qty = pending["qty"] if pending else 1
        unit = pending["unit"] if pending else ""
        original = pending["original"] if pending else ""

        inventory_manager.add_product(name)
        result = completions_manager.add_or_update(name, qty, actor)
        history_manager.log_action("הוספת מוצר חדש", name, actor, original, str(qty), unit or "")
        parser.update_product_names(inventory_manager.get_all_product_names())

        await query.edit_message_text(
            f"✅ *{name}* נוסף למלאי הקבוע ולרשימת היום!",
            parse_mode="Markdown"
        )

    elif data.startswith("add_temp:"):
        name = data.split(":", 1)[1]
        pending = context.user_data.pop("pending_add", None)
        qty = pending["qty"] if pending else 1
        unit = pending["unit"] if pending else ""
        original = pending["original"] if pending else ""

        result = completions_manager.add_or_update(name, qty, actor)
        history_manager.log_action("הוספת חוסר זמני", name, actor, original, str(qty), unit or "")

        await query.edit_message_text(
            f"📝 *{name}* נוסף לרשימת היום (ללא מלאי קבוע).",
            parse_mode="Markdown"
        )

    # ---- Category selection ----
    elif data.startswith("set_category:"):
        _, packed_name, category = data.split(":", 2)
        parts = packed_name.split("|")
        name = parts[0]
        target = parts[1] if len(parts) > 1 else ""
        unit = parts[2] if len(parts) > 2 else ""

        inventory_manager.add_product(name, category=category, target_qty=target, unit=unit)
        history_manager.log_action("הוספת מוצר למלאי", name, actor, details=f"קטגוריה: {category}")
        parser.update_product_names(inventory_manager.get_all_product_names())

        await query.edit_message_text(
            f"✅ *{name}* נוסף למלאי הקבוע בקטגוריה *{category}*.",
            parse_mode="Markdown"
        )

    # ---- Quick status buttons ----
    elif data.startswith("status:"):
        _, status, name = data.split(":", 2)
        ok = completions_manager.set_status(name, status, actor)
        if ok:
            history_manager.log_action(f"עדכון סטטוס -> {status}", name, actor)
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"✅ סטטוס *{name}* עודכן ל-*{status}*", parse_mode="Markdown")
        else:
            await query.answer(f"לא נמצא: {name}", show_alert=True)

    else:
        log.warning(f"Unhandled callback: {data}")
