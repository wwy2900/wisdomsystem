"""DashScope runtime configuration and error helpers."""

from __future__ import annotations

import os
import threading
from typing import Any

from utils.logger_handler import logger
from utils.network_env import dashscope_proxy_bypass_enabled, ensure_no_proxy_hosts


_RUNTIME_LOG_LOCK = threading.Lock()
_RUNTIME_LOGGED = False


def _read_int_env(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return max(minimum, int(raw_value))
    except ValueError:
        logger.warning(f"[DashScope] invalid integer env {name}={raw_value!r}, fallback to {default}")
        return default


def get_dashscope_request_timeout_seconds() -> int:
    return _read_int_env("DASHSCOPE_REQUEST_TIMEOUT_SECONDS", 20, minimum=1)


def get_dashscope_chat_max_retries() -> int:
    return _read_int_env("DASHSCOPE_CHAT_MAX_RETRIES", 1, minimum=0)


def get_dashscope_embedding_max_retries() -> int:
    return _read_int_env("DASHSCOPE_EMBEDDING_MAX_RETRIES", 1, minimum=0)


def get_semantic_checker_max_retries() -> int:
    return _read_int_env("SEMANTIC_CHECK_MAX_RETRIES", 1, minimum=1)


def apply_dashscope_runtime() -> dict[str, Any]:
    """Apply proxy/no_proxy safeguards and return the active runtime settings."""
    no_proxy_value = ensure_no_proxy_hosts()
    settings = {
        "proxy_mode": "direct" if dashscope_proxy_bypass_enabled() else "environment",
        "no_proxy": no_proxy_value,
        "request_timeout_seconds": get_dashscope_request_timeout_seconds(),
        "chat_max_retries": get_dashscope_chat_max_retries(),
        "embedding_max_retries": get_dashscope_embedding_max_retries(),
    }

    global _RUNTIME_LOGGED
    if not _RUNTIME_LOGGED:
        with _RUNTIME_LOG_LOCK:
            if not _RUNTIME_LOGGED:
                logger.info(
                    "[DashScope] runtime configured: mode=%s timeout=%ss chat_retries=%s embedding_retries=%s no_proxy=%s",
                    settings["proxy_mode"],
                    settings["request_timeout_seconds"],
                    settings["chat_max_retries"],
                    settings["embedding_max_retries"],
                    settings["no_proxy"] or "(empty)",
                )
                _RUNTIME_LOGGED = True

    return settings


def build_dashscope_error_payload(error: Exception) -> dict[str, str]:
    """Map low-level network/model exceptions to stable user-facing errors."""
    raw_message = str(error) or error.__class__.__name__
    normalized = raw_message.lower()

    if "dashscope.aliyuncs.com" in normalized and "ssleoferror" in normalized:
        return {
            "code": "dashscope_proxy_tls",
            "content": "DashScope request failed through the current proxy/TLS chain.",
            "detail": raw_message,
        }

    if "dashscope.aliyuncs.com" in normalized and "winerror 10013" in normalized:
        return {
            "code": "dashscope_direct_blocked",
            "content": "DashScope direct connection was blocked by the local machine or network policy.",
            "detail": raw_message,
        }

    if "timed out" in normalized or "readtimeout" in normalized or "request timeout" in normalized:
        return {
            "code": "upstream_timeout",
            "content": "The upstream model request timed out before completion.",
            "detail": raw_message,
        }

    return {
        "code": "upstream_error",
        "content": raw_message,
        "detail": raw_message,
    }
