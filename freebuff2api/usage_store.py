"""In-memory + JSONL storage for request records and API keys."""
from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock
from typing import Any

from .usage import ApiKeyRecord, RequestRecord


class RequestStore:
    """Ring-buffer store for request records with optional JSONL persistence."""

    def __init__(self, max_records: int = 5000, persist_path: str | None = None) -> None:
        self._max = max_records
        self._records: list[RequestRecord] = []
        self._next_id = 1
        self._lock = Lock()
        self._persist_path = persist_path

    def add(self, record: RequestRecord) -> None:
        with self._lock:
            record.id = self._next_id
            self._next_id += 1
            self._records.append(record)
            if len(self._records) > self._max:
                self._records = self._records[-self._max:]
            if self._persist_path:
                self._append_to_file(record)

    def list(
        self,
        since_id: int = 0,
        limit: int = 200,
        model: str | None = None,
        status: str | None = None,
        api_key_name: str | None = None,
    ) -> list[dict[str, Any]]:
        with self._lock:
            results = self._records
            if since_id > 0:
                results = [r for r in results if r.id > since_id]
            if model:
                results = [r for r in results if r.model == model]
            if status:
                results = [r for r in results if r.status == status]
            if api_key_name:
                results = [r for r in results if r.api_key_name == api_key_name]
            return [r.to_dict() for r in results[-limit:]]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            total = len(self._records)
            success = sum(1 for r in self._records if r.status == "success")
            error_count = total - success
            total_tokens = sum(r.total_tokens for r in self._records if r.status == "success")
            total_prompt = sum(r.prompt_tokens for r in self._records if r.status == "success")
            total_completion = sum(r.completion_tokens for r in self._records if r.status == "success")
            total_duration = sum(r.duration_ms for r in self._records)
            avg_duration = round(total_duration / total) if total > 0 else 0

            by_model: dict[str, dict[str, Any]] = {}
            for r in self._records:
                if r.model not in by_model:
                    by_model[r.model] = {"count": 0, "total_tokens": 0}
                by_model[r.model]["count"] += 1
                by_model[r.model]["total_tokens"] += r.total_tokens

            return {
                "total": total,
                "success": success,
                "error": error_count,
                "total_tokens": total_tokens,
                "total_prompt_tokens": total_prompt,
                "total_completion_tokens": total_completion,
                "avg_duration_ms": avg_duration,
                "by_model": by_model,
            }

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            if self._persist_path:
                p = Path(self._persist_path)
                if p.exists():
                    p.write_text("", encoding="utf-8")

    def _append_to_file(self, record: RequestRecord) -> None:
        try:
            p = Path(self._persist_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception:
            pass  # persistence is best-effort


class ApiKeyStore:
    """Manages multiple API keys from env / admin panel mutations."""

    def __init__(self) -> None:
        self._keys: dict[str, ApiKeyRecord] = {}
        self._lock = Lock()

    def load_from_settings(self, api_keys_json: str | None, fallback_key: str | None) -> None:
        """Parse FREEBUFF_API_KEYS JSON or fallback to single FREEBUFF_API_KEY."""
        with self._lock:
            self._keys.clear()
            if api_keys_json:
                try:
                    items = json.loads(api_keys_json)
                    for item in items:
                        rec = ApiKeyRecord(
                            name=str(item.get("name", "")).strip(),
                            key=str(item.get("key", "")).strip(),
                            allowed_models=item.get("allowed_models", ["*"]),
                            enabled=bool(item.get("enabled", True)),
                            created_at=str(item.get("created_at", "")),
                        )
                        if rec.name and rec.key:
                            self._keys[rec.name] = rec
                except (json.JSONDecodeError, TypeError):
                    pass
            if not self._keys and fallback_key:
                self._keys["default"] = ApiKeyRecord(
                    name="default", key=fallback_key, allowed_models=["*"], enabled=True
                )

    def authenticate(self, auth_header: str | None, x_api_key: str | None) -> ApiKeyRecord | None:
        """Try to match Authorization Bearer or x-api-key against stored keys."""
        with self._lock:
            for rec in self._keys.values():
                if not rec.enabled:
                    continue
                if auth_header == f"Bearer {rec.key}":
                    return rec
                if x_api_key == rec.key:
                    return rec
        return None

    def list_all(self) -> list[dict[str, Any]]:
        with self._lock:
            return [rec.to_dict(mask=True) for rec in self._keys.values()]

    def get(self, name: str) -> ApiKeyRecord | None:
        with self._lock:
            return self._keys.get(name)

    def add(self, rec: ApiKeyRecord) -> None:
        with self._lock:
            self._keys[rec.name] = rec

    def update(self, name: str, **fields: Any) -> bool:
        with self._lock:
            if name not in self._keys:
                return False
            rec = self._keys[name]
            if "key" in fields and fields["key"]:
                rec.key = fields["key"]
            if "allowed_models" in fields:
                rec.allowed_models = fields["allowed_models"]
            if "enabled" in fields:
                rec.enabled = fields["enabled"]
            return True

    def delete(self, name: str) -> bool:
        with self._lock:
            if name not in self._keys:
                return False
            del self._keys[name]
            return True

    def to_env_json(self) -> str:
        with self._lock:
            items = [rec.to_dict(mask=False) for rec in self._keys.values()]
            return json.dumps(items, ensure_ascii=False)

    @property
    def count(self) -> int:
        with self._lock:
            return len([k for k in self._keys.values() if k.enabled])

    @property
    def total_count(self) -> int:
        with self._lock:
            return len(self._keys)


def _data_dir() -> Path:
    """Resolve data directory relative to the project root."""
    return Path(__file__).resolve().parents[1] / "data"


def create_stores(max_records: int) -> tuple[RequestStore, ApiKeyStore]:
    persist = str(_data_dir() / "request_records.jsonl")
    return RequestStore(max_records=max_records, persist_path=persist), ApiKeyStore()
