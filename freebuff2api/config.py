from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


HAR_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

DEFAULT_ADMIN_KEY = "sk-admin"


@dataclass(frozen=True)
class Settings:
    codebuff_token: str | None
    local_api_key: str | None
    admin_key: str | None = None
    codebuff_base_url: str = "https://www.codebuff.com"
    zeroclick_base_url: str = "https://zeroclick.dev"
    session_id: str = ""
    client_id: str = ""
    ad_providers: tuple[str, ...] = ("gravity", "zeroclick")
    request_timeout: float = 60.0
    debug: bool = False
    log_level: str = "INFO"
    log_body_chars: int = 2000
    log_color: bool = True
    admin_log_lines: int = 1000
    host: str = "0.0.0.0"
    port: int = 8000
    proxy_enabled: bool = False
    proxy_url: str | None = None
    timezone: str = "Asia/Shanghai"
    locale: str = "zh-CN"
    os_name: str = "windows"
    system_prompt_override: str | None = None
    api_keys_json: str | None = None
    max_request_records: int = 5000

    @property
    def codebuff_api_url(self) -> str:
        return self.codebuff_base_url.strip().rstrip("/")

    @property
    def zeroclick_api_url(self) -> str:
        return self.zeroclick_base_url.rstrip("/")

    @property
    def upstream_proxy_url(self) -> str | None:
        if not self.proxy_enabled:
            return None
        if not self.proxy_url:
            return None
        return self.proxy_url.strip() or None

    @property
    def codebuff_tokens(self) -> tuple[str, ...]:
        if not self.codebuff_token:
            return ()
        values = [item.strip() for item in self.codebuff_token.split(",")]
        return tuple(item for item in values if item)


def _csv(name: str, default: str) -> tuple[str, ...]:
    values = [item.strip() for item in os.getenv(name, default).split(",")]
    return tuple(item for item in values if item)


def _bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _api_base_url() -> str:
    return (
        os.getenv("FREEBUFF_API_BASE_URL")
        or os.getenv("CODEBUFF_BASE_URL")
        or "https://www.codebuff.com"
    )


def load_settings() -> Settings:
    debug = _bool("FREEBUFF_DEBUG", False)
    log_level = "DEBUG" if debug else os.getenv("FREEBUFF_LOG_LEVEL", "INFO")
    color_default = os.getenv("NO_COLOR") is None
    return Settings(
        codebuff_token=os.getenv("FREEBUFF_TOKEN") or os.getenv("CODEBUFF_TOKEN"),
        local_api_key=os.getenv("FREEBUFF_API_KEY") or os.getenv("OPENAI_API_KEY"),
        admin_key=os.getenv("FREEBUFF_ADMIN_KEY") or DEFAULT_ADMIN_KEY,
        codebuff_base_url=_api_base_url(),
        zeroclick_base_url=os.getenv("ZEROCLICK_BASE_URL", "https://zeroclick.dev"),
        session_id=os.getenv("FREEBUFF_SESSION_ID", str(uuid.uuid4())),
        client_id=os.getenv("FREEBUFF_CLIENT_ID", uuid.uuid4().hex[:11]),
        ad_providers=_csv("FREEBUFF_AD_PROVIDERS", "gravity,zeroclick"),
        request_timeout=float(os.getenv("FREEBUFF_TIMEOUT", "60")),
        debug=debug,
        log_level=log_level,
        log_body_chars=_int("FREEBUFF_LOG_BODY_CHARS", 0 if debug else 2000),
        log_color=_bool("FREEBUFF_LOG_COLOR", color_default),
        admin_log_lines=_int("FREEBUFF_ADMIN_LOG_LINES", 1000),
        host=os.getenv("FREEBUFF_HOST", "0.0.0.0"),
        port=_int("FREEBUFF_PORT", 8000),
        proxy_enabled=_bool("FREEBUFF_PROXY_ENABLED", False),
        proxy_url=os.getenv("FREEBUFF_PROXY_URL"),
        timezone=os.getenv("FREEBUFF_TIMEZONE", "Asia/Shanghai"),
        locale=os.getenv("FREEBUFF_LOCALE", "zh-CN"),
        os_name=os.getenv("FREEBUFF_OS", "windows"),
        system_prompt_override=os.getenv("FREEBUFF_SYSTEM_PROMPT_OVERRIDE"),
        api_keys_json=os.getenv("FREEBUFF_API_KEYS"),
        max_request_records=_int("FREEBUFF_MAX_REQUEST_RECORDS", 5000),
    )


def project_env_path() -> Path:
    return Path(__file__).resolve().parents[1] / ".env"


def write_env_values(values: dict[str, str | None], env_path: Path | None = None) -> None:
    path = env_path or project_env_path()
    existing = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    pending = dict(values)
    output: list[str] = []

    for line in existing:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue
        name = line.split("=", 1)[0].strip()
        if name in pending:
            value = pending.pop(name)
            if value is not None:
                output.append(f"{name}={value}")
            continue
        output.append(line)

    for name, value in pending.items():
        if value is not None:
            output.append(f"{name}={value}")

    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
