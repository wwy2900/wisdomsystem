"""Migrate tests/test_cases.json into eval/rag_cases.jsonl with heuristic prefill."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from eval.eval_utils import EVAL_DIR, load_chunks_snapshot, save_jsonl

TEST_CASES_PATH = EVAL_DIR.parent / "tests" / "test_cases.json"
OUTPUT_PATH = EVAL_DIR / "rag_cases.jsonl"

_TROUBLESHOOT_KW = ("wifi", "连不上", "卡住", "不转", "没反应", "找不到", "报错", "异常", "故障", "失灵")
_SERVICE_KW = ("保修", "维修", "退换", "客服", "售后", "换货")
_CONSUMABLE_KW = ("清洗", "更换", "滤网", "边刷", "滚刷", "耗材", "尘盒", "滤芯")


def _classify_category(query: str) -> str:
    q = query.lower()
    if any(kw in q for kw in _TROUBLESHOOT_KW):
        return "故障排查"
    if any(kw in q for kw in _SERVICE_KW):
        return "售后服务"
    if any(kw in q for kw in _CONSUMABLE_KW):
        return "耗材维护"
    return "知识库问答"


def _char_overlap_ratio(query_terms: list[str], content: str) -> float:
    if not query_terms or not content:
        return 0.0
    hits = sum(1 for term in query_terms if term and term in content)
    return hits / len(query_terms) if query_terms else 0.0


def heuristic_prefill_doc_ids(
    query: str,
    keywords: list[str],
    chunks: list[dict],
    threshold: float = 0.15,
    top_n: int = 3,
) -> list[str]:
    if not chunks:
        return []

    query_terms = [t for t in re.split(r"[\s,，。.?？!！、]+", query) if t]
    query_terms.extend(keywords)
    query_terms = [t for t in query_terms if t]

    scored: list[tuple[str, float]] = []
    for chunk in chunks:
        doc_id = chunk.get("doc_id", "")
        content = chunk.get("content", "") or ""
        if not doc_id or not content:
            continue
        ratio = _char_overlap_ratio(query_terms, content)
        if ratio >= threshold:
            scored.append((doc_id, ratio))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [doc_id for doc_id, _ in scored[:top_n]]


def migrate() -> list[dict]:
    if not TEST_CASES_PATH.exists():
        raise FileNotFoundError(f"Test cases file not found: {TEST_CASES_PATH}")

    with open(TEST_CASES_PATH, "r", encoding="utf-8") as f:
        old_cases = json.load(f)

    chunks_snapshot = load_chunks_snapshot()
    if chunks_snapshot is None:
        print("[migrate] chunks_snapshot.json not found; expected_doc_ids will be empty.")
        print("[migrate] Run `python eval/export_chunks.py --limit 1000` first to enable heuristic prefill.")

    new_cases: list[dict] = []
    heuristic_count = 0
    need_label_count = 0

    for old in old_cases:
        old_id = old.get("id", "")
        new_id = old_id.replace("test_", "rag_") if old_id.startswith("test_") else f"rag_{old_id}"
        query = old.get("user_query", "")
        keywords = old.get("expected_keywords", []) or []
        relevant = old.get("relevant_doc_ids", []) or []

        if relevant:
            expected_doc_ids = relevant
            label_status = "labeled"
        elif chunks_snapshot:
            expected_doc_ids = heuristic_prefill_doc_ids(query, keywords, chunks_snapshot)
            label_status = "heuristic" if expected_doc_ids else "need_label"
        else:
            expected_doc_ids = []
            label_status = "need_label"

        if label_status == "heuristic":
            heuristic_count += 1
        else:
            need_label_count += 1

        new_cases.append(
            {
                "id": new_id,
                "category": _classify_category(query),
                "user_id": "__shared__",
                "query": query,
                "expected_doc_ids": expected_doc_ids,
                "expected_keywords": keywords,
                "must_cite": True,
                "label_status": label_status,
                "note": old.get("note", ""),
            }
        )

    save_jsonl(OUTPUT_PATH, new_cases)
    print(f"[migrate] migrated {len(new_cases)} cases -> {OUTPUT_PATH}")
    print(f"[migrate] heuristic: {heuristic_count}, need_label: {need_label_count}")
    return new_cases


if __name__ == "__main__":
    migrate()
