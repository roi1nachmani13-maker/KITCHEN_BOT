"""
Configuration management - loads from .env file.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Telegram
    telegram_bot_token: str = ""
    admin_user_ids: List[int] = field(default_factory=list)

    # Google Sheets
    google_service_account_json: str = ""
    google_service_account_json_content: str = ""
    spreadsheet_id: str = ""

    # Bot behavior
    bot_language: str = "he"
    timezone: str = "Asia/Jerusalem"
    fuzzy_threshold: int = 75

    # Backup
    backup_enabled: bool = True
    backup_hour: int = 23
    backup_minute: int = 30

    # Daily summary
    daily_summary_enabled: bool = True
    daily_summary_hour: int = 22
    daily_summary_minute: int = 0

    @classmethod
    def from_env(cls) -> "Config":
        admin_ids_raw = os.getenv("ADMIN_USER_IDS", "")
        admin_ids = [
            int(x.strip())
            for x in admin_ids_raw.split(",")
            if x.strip().isdigit()
        ]

        return cls(
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            admin_user_ids=admin_ids,
            google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", ""),
            google_service_account_json_content=os.getenv(
                "GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT", ""
            ),
            spreadsheet_id=os.getenv("SPREADSHEET_ID", ""),
            bot_language=os.getenv("BOT_LANGUAGE", "he"),
            timezone=os.getenv("TIMEZONE", "Asia/Jerusalem"),
            fuzzy_threshold=int(os.getenv("FUZZY_THRESHOLD", "75")),
            backup_enabled=os.getenv("BACKUP_ENABLED", "true").lower() == "true",
            backup_hour=int(os.getenv("BACKUP_HOUR", "23")),
            backup_minute=int(os.getenv("BACKUP_MINUTE", "30")),
            daily_summary_enabled=os.getenv(
                "DAILY_SUMMARY_ENABLED", "true"
            ).lower()
            == "true",
            daily_summary_hour=int(os.getenv("DAILY_SUMMARY_HOUR", "22")),
            daily_summary_minute=int(os.getenv("DAILY_SUMMARY_MINUTE", "0")),
        )

    def validate(self) -> None:
        errors = []
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is missing")
        if not self.spreadsheet_id:
            errors.append("SPREADSHEET_ID is missing")
        if not self.google_service_account_json and not self.google_service_account_json_content:
            errors.append(
                "Either GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_JSON_CONTENT must be set"
            )
        if errors:
            raise ValueError("Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors))

    def get_service_account_info(self) -> dict:
        """Return parsed service account credentials dict."""
        if self.google_service_account_json_content:
            return json.loads(self.google_service_account_json_content)
        with open(self.google_service_account_json, "r", encoding="utf-8") as f:
            return json.load(f)


# Singleton
config = Config.from_env()
