"""Common utilities for the quantitative evaluation framework."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

EVAL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = EVAL_DIR.parent
REPORT_DIR = EVAL_DIR / "reports"

_TOOL_PATTERN = re.compile(r"\[TOOL:([a-zA-Z_][a-zA-Z0-9_]*):")
_TOOL_RESULT_PATTERN = re.compile(r"\[TOOL_RESULT:([a-zA-Z_][a-zA-Z0-9_]*):")

_REFUSAL_HINTS = (
    "不确定",
    "未提供",
    "建议联系",
    "需要更多",
    "无法确认",
    "知识库未",
    "知识库中未",
    "没有相关",
    "暂无",
    "无法回答",
    "不在",
    "不清楚",
    "没有提到",
    "没有涉及",
)


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSONL file, skipping blank lines."""
    items: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    return items


def save_json(path: str | Path, data: Any) -> None:
    """Write pretty JSON with UTF-8."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_jsonl(path: str | Path, items: list[dict[str, Any]]) -> None:
    """Write a JSONL file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def ensure_report_dir() -> Path:
    """Return the reports directory, creating it if needed."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return REPORT_DIR


def percentile(values: list[float], p: float) -> float:
    """Linear interpolation percentile without numpy."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * p
    lower = int(rank)
    upper = min(lower + 1, len(ordered) - 1)
    weight = rank - lower
    return float(ordered[lower] * (1 - weight) + ordered[upper] * weight)


def keyword_coverage(text: str, keywords: list[str]) -> float:
    """Fraction of keywords present in text."""
    if not keywords:
        return 0.0
    hits = sum(1 for kw in keywords if kw and kw in text)
    return hits / len(keywords)


def normalize_tool_name(raw: str) -> str:
    """Normalize a tool name extracted from stream markers."""
    return raw.strip().lower()


def extract_tool_names_from_chunks(chunks: list[str]) -> list[str]:
    """Extract tool names from [TOOL:name:...] and [TOOL_RESULT:name:...] markers.

    Returns de-duplicated names in first-seen order.
    """
    names: list[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        for pattern in (_TOOL_PATTERN, _TOOL_RESULT_PATTERN):
            for match in pattern.finditer(chunk):
                name = match.group(1)
                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
    return names


def has_forbidden_keyword(text: str, forbidden: list[str]) -> bool:
    """Return True if any forbidden keyword appears in text."""
    return any(kw and kw in text for kw in forbidden)


def is_refusal_or_clarify(text: str) -> bool:
    """Rule-based check: does the answer refuse or ask for clarification?"""
    if not text or not text.strip():
        return True
    return any(hint in text for hint in _REFUSAL_HINTS)


def load_chunks_snapshot() -> list[dict[str, Any]] | None:
    """Load exported chunk snapshot if available."""
    snapshot_path = REPORT_DIR / "chunks_snapshot.json"
    if not snapshot_path.exists():
        return None
    try:
        with open(snapshot_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("chunks") or data.get("items") or []
    except Exception:
        return None
