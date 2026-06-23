"""Request usage data models for the admin panel."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RequestRecord:
    id: int
    timestamp: str  # ISO 8601
    api_key_name: str
    api_key_prefix: str  # first 8 chars for masking
    model: str
    duration_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    status: str  # "success" | "error"
    error: str | None = None
    client_ip: str | None = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "api_key_name": self.api_key_name,
            "api_key_prefix": self.api_key_prefix,
            "model": self.model,
            "duration_ms": self.duration_ms,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "status": self.status,
            "error": self.error,
            "client_ip": self.client_ip,
        }


@dataclass
class ApiKeyRecord:
    name: str
    key: str
    allowed_models: list[str] = field(default_factory=lambda: ["*"])
    enabled: bool = True
    created_at: str = ""

    @property
    def prefix(self) -> str:
        return self.key[:8] if len(self.key) >= 8 else self.key[:4]

    def allows_model(self, model_id: str) -> bool:
        if "*" in self.allowed_models:
            return True
        return model_id in self.allowed_models

    def to_dict(self, *, mask: bool = True) -> dict:
        return {
            "name": self.name,
            "key": _mask(self.key) if mask else self.key,
            "key_prefix": self.prefix,
            "allowed_models": self.allowed_models,
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


def _mask(value: str, keep: int = 6) -> str:
    if not value:
        return ""
    if len(value) <= keep * 2:
        return "*" * len(value)
    return f"{value[:keep]}...{value[-keep:]}"
