"""SSE / streaming performance benchmark: TTFT, Total Latency, P50/P95."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from eval.eval_utils import EVAL_DIR, ensure_report_dir, load_jsonl, percentile, save_json

DEFAULT_CASES = EVAL_DIR / "rag_cases.jsonl"
DEFAULT_LIMIT = 20
DEFAULT_USER_ID = "user_74bbef07baf54e0cba54d665a6cfa035"


def _benchmark_service(query: str, user_id: str, session_id: str) -> dict:
    from services.chat_service import ChatService

    service = ChatService()
    start = time.perf_counter()
    ttft = None
    total = None
    answer_parts: list[str] = []

    for event_type, payload in service.chat_stream(user_id, session_id, query):
        if event_type == "answer_delta" and ttft is None:
            ttft = (time.perf_counter() - start) * 1000
        if event_type == "_done":
            total = (time.perf_counter() - start) * 1000

    if total is None:
        total = (time.perf_counter() - start) * 1000

    return {
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "total_ms": round(total, 2),
        "answer": "".join(answer_parts)[:200],
    }


def _benchmark_http(query: str, base_url: str, api_key: str, user_id: str, session_id: str) -> dict:
    import requests

    url = base_url.rstrip("/") + "/api/v1/chat/stream"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    payload = {"user_id": user_id, "session_id": session_id, "message": query}

    start = time.perf_counter()
    ttft = None
    total = None

    try:
        response = requests.post(url, json=payload, headers=headers, stream=True, timeout=120)
        response.raise_for_status()

        event_type = None
        for raw_line in response.iter_lines(decode_unicode=True):
            if not raw_line:
                continue
            if raw_line.startswith("event:"):
                event_type = raw_line[len("event:"):].strip()
            elif raw_line.startswith("data:"):
                data_str = raw_line[len("data:"):].strip()
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if event_type == "answer_delta" and ttft is None:
                    ttft = (time.perf_counter() - start) * 1000
                if event_type == "done":
                    total = (time.perf_counter() - start) * 1000
    except Exception as exc:
        return {
            "ttft_ms": None,
            "total_ms": round((time.perf_counter() - start) * 1000, 2),
            "error": str(exc),
        }

    if total is None:
        total = (time.perf_counter() - start) * 1000

    return {
        "ttft_ms": round(ttft, 2) if ttft is not None else None,
        "total_ms": round(total, 2),
    }


def benchmark(
    cases_path: str | Path = DEFAULT_CASES,
    mode: str = "service",
    limit: int = DEFAULT_LIMIT,
    base_url: str = "http://127.0.0.1:8000",
    api_key: str = "",
    user_id: str = DEFAULT_USER_ID,
) -> dict:
    cases = load_jsonl(cases_path)
    if not cases:
        print("[benchmark_stream] no cases found.")
        return {
            "mode": mode,
            "case_count": 0,
            "p50_ttft_ms": 0.0,
            "p95_ttft_ms": 0.0,
            "p50_total_ms": 0.0,
            "p95_total_ms": 0.0,
            "details": [],
        }

    selected = cases[:limit]
    details: list[dict] = []
    ttft_values: list[float] = []
    total_values: list[float] = []

    for idx, case in enumerate(selected):
        query = case.get("query", "")
        session_id = f"bench_{idx}"
        print(f"[benchmark_stream] ({idx + 1}/{len(selected)}) {query[:40]}")

        if mode == "http":
            result = _benchmark_http(query, base_url, api_key, user_id, session_id)
        else:
            result = _benchmark_service(query, user_id, session_id)

        result["query"] = query
        details.append(result)

        if result.get("ttft_ms") is not None:
            ttft_values.append(result["ttft_ms"])
        if result.get("total_ms") is not None:
            total_values.append(result["total_ms"])

    return {
        "mode": mode,
        "case_count": len(details),
        "p50_ttft_ms": round(percentile(ttft_values, 0.50), 2),
        "p95_ttft_ms": round(percentile(ttft_values, 0.95), 2),
        "p50_total_ms": round(percentile(total_values, 0.50), 2),
        "p95_total_ms": round(percentile(total_values, 0.95), 2),
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="SSE / streaming performance benchmark")
    parser.add_argument("--mode", choices=["service", "http"], default="service")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--api-key", default=os.environ.get("FASTAPI_API_KEY", "legacy_fastapi_api_key"))
    parser.add_argument("--user-id", default=DEFAULT_USER_ID)
    args = parser.parse_args()

    report = benchmark(
        cases_path=args.cases,
        mode=args.mode,
        limit=args.limit,
        base_url=args.base_url,
        api_key=args.api_key,
        user_id=args.user_id,
    )
    out_path = ensure_report_dir() / "stream_benchmark_report.json"
    save_json(out_path, report)
    print(f"[benchmark_stream] report saved to {out_path}")
    print(
        f"  p50_ttft={report['p50_ttft_ms']}ms  "
        f"p95_ttft={report['p95_ttft_ms']}ms  "
        f"p50_total={report['p50_total_ms']}ms  "
        f"p95_total={report['p95_total_ms']}ms"
    )


if __name__ == "__main__":
    main()
