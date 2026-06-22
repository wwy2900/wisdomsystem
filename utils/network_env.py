"""Helpers for process-level network environment safeguards."""

import os


DASHSCOPE_NO_PROXY_HOSTS = (
    "dashscope.aliyuncs.com",
    ".aliyuncs.com",
)


def ensure_no_proxy_hosts(hosts: tuple[str, ...] = DASHSCOPE_NO_PROXY_HOSTS) -> str:
    """Append host patterns to NO_PROXY/no_proxy without dropping existing entries."""
    raw_values = [
        os.getenv("NO_PROXY", ""),
        os.getenv("no_proxy", ""),
    ]
    current_entries: list[str] = []

    for raw_value in raw_values:
        for item in raw_value.split(","):
            normalized = item.strip()
            if normalized and normalized not in current_entries:
                current_entries.append(normalized)

    for host in hosts:
        normalized = host.strip()
        if normalized and normalized not in current_entries:
            current_entries.append(normalized)

    merged = ",".join(current_entries)
    os.environ["NO_PROXY"] = merged
    os.environ["no_proxy"] = merged
    return merged
