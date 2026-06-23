"""Customer support read-only data service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from database.sqlite_db import SQLiteDatabase
from utils.config_handler import agent_conf
from utils.path_tool import get_abs_path


class CustomerSupportService:
    def __init__(self, db: SQLiteDatabase | None = None):
        self.db = db or SQLiteDatabase()
        data_dir = agent_conf.get("customer_support_data_dir", "data/customer_support")
        self.data_dir = Path(get_abs_path(data_dir))
        self._policy_records = self._load_json("service_policies.json")
        self._channel_records = self._load_json("service_channels.json")

    def _load_json(self, filename: str) -> list[dict[str, Any]]:
        file_path = self.data_dir / filename
        if not file_path.exists():
            return []
        with open(file_path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, list) else []

    def list_user_devices(self, user_id: str) -> list[dict[str, Any]]:
        return self.db.list_customer_devices(user_id)

    def get_device(self, user_id: str, device_id: str | None = None) -> dict[str, Any] | None:
        if device_id:
            return self.db.get_customer_device(device_id=device_id, user_id=user_id)

        devices = self.list_user_devices(user_id)
        if not devices:
            return None
        return next((item for item in devices if item.get("is_default")), devices[0])

    def list_device_consumables(self, user_id: str, device_id: str | None = None) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        device = self.get_device(user_id=user_id, device_id=device_id)
        if not device:
            return None, []
        return device, self.db.list_device_consumables(device["device_id"])

    @staticmethod
    def _score_keywords(record: dict[str, Any], query: str) -> int:
        normalized_query = (query or "").strip().lower()
        if not normalized_query:
            return 1

        score = 0
        haystacks = [
            str(record.get("title", "")),
            str(record.get("category", "")),
            str(record.get("content", "")),
            str(record.get("service_hours", "")),
            str(record.get("contact", "")),
            str(record.get("address", "")),
        ]
        keywords = [str(item) for item in record.get("keywords", [])]

        for value in haystacks + keywords:
            lowered = value.lower()
            if normalized_query in lowered:
                score += 3
            for token in normalized_query.split():
                if token and token in lowered:
                    score += 1
        return score

    def search_service_policies(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        ranked = sorted(
            self._policy_records,
            key=lambda record: self._score_keywords(record, query),
            reverse=True,
        )
        return [record for record in ranked if self._score_keywords(record, query) > 0][:limit]

    def search_service_channels(self, query: str = "", limit: int = 3) -> list[dict[str, Any]]:
        ranked = sorted(
            self._channel_records,
            key=lambda record: self._score_keywords(record, query),
            reverse=True,
        )
        return [record for record in ranked if self._score_keywords(record, query) > 0][:limit]
