"""
Message formatting helpers for Telegram output.
"""
from __future__ import annotations

from typing import List, Dict, Optional
from datetime import datetime
import pytz

from src.utils.config import config

TZ = pytz.timezone(config.timezone)

# Status emojis
STATUS_EMOJI: Dict[str, str] = {
    "פתוח": "□",
    "בטיפול": "🔄",
    "נקנה": "✓",
    "בוטל": "✗",
    "הוחזר": "↩",
}


def now_local() -> datetime:
    return datetime.now(TZ)


def format_date(dt: Optional[datetime] = None) -> str:
    dt = dt or now_local()
    return dt.strftime("%d/%m/%Y")


def format_time(dt: Optional[datetime] = None) -> str:
    dt = dt or now_local()
    return dt.strftime("%H:%M")


def format_datetime(dt: Optional[datetime] = None) -> str:
    dt = dt or now_local()
    return dt.strftime("%d/%m/%Y %H:%M")


def format_completions_list(items: List[Dict]) -> str:
    """Format completions list for Telegram display."""
    if not items:
        return "📋 *רשימת השלמות להיום ריקה*\n\nשלח שם מוצר להוספה."

    # Group by status
    active = [i for i in items if i.get("סטטוס") in ("פתוח", "בטיפול", "הוחזר")]
    done = [i for i in items if i.get("סטטוס") == "נקנה"]
    cancelled = [i for i in items if i.get("סטטוס") == "בוטל"]

    lines = [f"📋 *השלמות להיום – {format_date()}*\n"]

    # Group active by category
    if active:
        by_cat: Dict[str, List[Dict]] = {}
        for item in active:
            cat = item.get("קטגוריה", "כללי") or "כללי"
            by_cat.setdefault(cat, []).append(item)

        for cat, cat_items in sorted(by_cat.items()):
            lines.append(f"*{cat}*")
            for item in cat_items:
                emoji = STATUS_EMOJI.get(item.get("סטטוס", "פתוח"), "□")
                name = item.get("שם מוצר", "")
                qty = item.get("כמות חסרה", "")
                unit = item.get("יחידת מידה", "")
                note = item.get("הערות", "")
                line = f"  {emoji} {name}"
                if qty:
                    line += f" – {qty}"
                if unit:
                    line += f" {unit}"
                if note:
                    line += f" _(_{note}_)_"
                lines.append(line)
        lines.append("")

    if done:
        lines.append("*✅ הושלם:*")
        for item in done:
            name = item.get("שם מוצר", "")
            lines.append(f"  ✓ {name}")
        lines.append("")

    if cancelled:
        lines.append("*❌ בוטל:*")
        for item in cancelled:
            name = item.get("שם מוצר", "")
            lines.append(f"  ✗ {name}")

    total = len(active)
    total_done = len(done)
    lines.append(f"\n_פתוחים: {total} | הושלמו: {total_done}_")

    return "\n".join(lines)


def format_inventory_list(items: List[Dict]) -> str:
    """Format permanent inventory for display."""
    if not items:
        return "📦 *המלאי הקבוע ריק*\n\nהשתמש ב-/הוסף_מוצר להוספה."

    lines = ["📦 *מלאי קבוע – מוצרים פעילים*\n"]

    by_cat: Dict[str, List[Dict]] = {}
    for item in items:
        cat = item.get("קטגוריה", "כללי") or "כללי"
        by_cat.setdefault(cat, []).append(item)

    for cat, cat_items in sorted(by_cat.items()):
        lines.append(f"*{cat}*")
        for item in cat_items:
            name = item.get("שם מוצר", "")
            target = item.get("כמות יעד", "")
            unit = item.get("יחידת מידה", "")
            line = f"  • {name}"
            if target:
                line += f" – יעד: {target}"
            if unit:
                line += f" {unit}"
            lines.append(line)
        lines.append("")

    total_str = f"סה\"כ {len(items)} מוצרים"
    lines.append(f"_{total_str}_")
    return "\n".join(lines)


def format_daily_report(stats: Dict) -> str:
    """Format end-of-day report."""
    lines = [
        f"📊 *דוח יומי – {format_date()}*\n",
        f"✅ הושלמו: {stats.get('נקנה', 0)}",
        f"□ פתוחים: {stats.get('פתוח', 0)}",
        f"🔄 בטיפול: {stats.get('בטיפול', 0)}",
        f"❌ בוטלו: {stats.get('בוטל', 0)}",
        f"↩ הוחזרו: {stats.get('הוחזר', 0)}",
        f"\n_סה\"כ פריטים: {stats.get('סהכ', 0)}_",
    ]
    return "\n".join(lines)
