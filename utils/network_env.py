"""Helpers for process-level network environment safeguards."""

import os


DASHSCOPE_NO_PROXY_HOSTS = (
    "dashscope.aliyuncs.com",
    ".aliyuncs.com",
)

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def dashscope_proxy_bypass_enabled() -> bool:
    """Return True only when the caller explicitly opts into bypassing proxies."""
    raw_value = os.getenv("DASHSCOPE_BYPASS_PROXY", "")
    return raw_value.strip().lower() in _TRUTHY_VALUES


def _collect_no_proxy_entries() -> list[str]:
    entries: list[str] = []
    for raw_value in (os.getenv("NO_PROXY", ""), os.getenv("no_proxy", "")):
        for item in raw_value.split(","):
            normalized = item.strip()
            if normalized and normalized not in entries:
                entries.append(normalized)
    return entries


def ensure_no_proxy_hosts(
    hosts: tuple[str, ...] = DASHSCOPE_NO_PROXY_HOSTS,
    enabled: bool | None = None,
) -> str:
    """Append host patterns to NO_PROXY/no_proxy only when bypass is enabled."""
    current_entries = _collect_no_proxy_entries()
    should_bypass = dashscope_proxy_bypass_enabled() if enabled is None else enabled

    if not should_bypass:
        merged = ",".join(current_entries)
        if current_entries:
            os.environ["NO_PROXY"] = merged
            os.environ["no_proxy"] = merged
        return merged

    for host in hosts:
        normalized = host.strip()
        if normalized and normalized not in current_entries:
            current_entries.append(normalized)

    merged = ",".join(current_entries)
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged
    return merged
