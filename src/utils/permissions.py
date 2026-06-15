"""
User permission management.
Admin IDs are loaded from config; can be extended at runtime.
"""
from __future__ import annotations

from src.utils.config import config
from src.utils.logger import get_logger

log = get_logger(__name__)

# Runtime-mutable admin set (seeded from config)
_admin_ids: set[int] = set(config.admin_user_ids)


def is_admin(user_id: int) -> bool:
    return user_id in _admin_ids


def add_admin(user_id: int) -> None:
    _admin_ids.add(user_id)
    log.info(f"Added admin: {user_id}")


def remove_admin(user_id: int) -> None:
    _admin_ids.discard(user_id)
    log.info(f"Removed admin: {user_id}")


def list_admins() -> list[int]:
    return sorted(_admin_ids)
