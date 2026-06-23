"""Agent tool selection evaluation via ChatService.chat_stream."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from eval.eval_utils import (
    EVAL_DIR,
    ensure_report_dir,
    extract_tool_names_from_chunks,
    load_jsonl,
    save_json,
)

DEFAULT_CASES = EVAL_DIR / "agent_cases.jsonl"


def _evaluate_case(service, case: dict) -> dict:
    case_id = case.get("id", "")
    query = case["query"]
    expected_tool = case.get("expected_tool", "")
    user_id = case.get("user_id", "default")
    session_id = f"eval_{case_id}"

    called_tools: list[str] = []
    first_tool: str | None = None
    has_tool_result = False
    has_error = False
    has_sources = False
    answer_parts: list[str] = []

    try:
        for event_type, payload in service.chat_stream(user_id, session_id, query):
            if event_type == "tool_event":
                content = payload.get("content", "")
                tools = extract_tool_names_from_chunks([content])
                for tool in tools:
                    if tool not in called_tools:
                        called_tools.append(tool)
                        if first_tool is None:
                            first_tool = tool
                if "[TOOL_RESULT" in content:
                    has_tool_result = True
                    if "error" in content.lower():
                        has_error = True
            elif event_type == "answer_delta":
                answer_parts.append(payload.get("content", ""))
            elif event_type == "_done":
                sources = payload.get("sources") or []
                has_sources = len(sources) > 0
    except Exception as exc:
        return {
            "id": case_id,
            "query": query,
            "expected_tool": expected_tool,
            "called_tools": called_tools,
            "first_tool": first_tool,
            "has_tool_result": has_tool_result,
            "has_error": True,
            "has_sources": has_sources,
            "answer": "".join(answer_parts)[:300],
            "passed": False,
            "error": str(exc),
        }

    passed = expected_tool in called_tools
    return {
        "id": case_id,
        "query": query,
        "expected_tool": expected_tool,
        "called_tools": called_tools,
        "first_tool": first_tool,
        "has_tool_result": has_tool_result,
        "has_error": has_error,
        "has_sources": has_sources,
        "answer": "".join(answer_parts)[:300],
        "passed": passed,
    }


def evaluate(cases_path: str | Path = DEFAULT_CASES) -> dict:
    cases = load_jsonl(cases_path)
    if not cases:
        print("[evaluate_agent] no cases found.")
        return {
            "total": 0,
            "tool_selection_accuracy": 0.0,
            "first_tool_accuracy": 0.0,
            "tool_success_rate": 0.0,
            "source_rate": 0.0,
            "details": [],
        }

    from services.chat_service import ChatService

    service = ChatService()
    details: list[dict] = []
    selection_count = 0
    first_tool_count = 0
    success_count = 0
    source_count = 0
    tool_called_count = 0

    for case in cases:
        print(f"[evaluate_agent] case {case.get('id', '')}: {case['query'][:40]}")
        result = _evaluate_case(service, case)
        details.append(result)

        if result["passed"]:
            selection_count += 1
        if result["first_tool"] == case.get("expected_tool"):
            first_tool_count += 1
        if result["called_tools"]:
            tool_called_count += 1
            if result["has_tool_result"] and not result["has_error"]:
                success_count += 1
        if result["has_sources"]:
            source_count += 1

    total = len(details)
    return {
        "total": total,
        "tool_selection_accuracy": round(selection_count / total, 4) if total else 0.0,
        "first_tool_accuracy": round(first_tool_count / total, 4) if total else 0.0,
        "tool_success_rate": round(success_count / tool_called_count, 4) if tool_called_count else 0.0,
        "source_rate": round(source_count / total, 4) if total else 0.0,
        "details": details,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent tool selection evaluation")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    args = parser.parse_args()

    report = evaluate(cases_path=args.cases)
    out_path = ensure_report_dir() / "agent_report.json"
    save_json(out_path, report)
    print(f"[evaluate_agent] report saved to {out_path}")
    print(
        f"  tool_selection_accuracy={report['tool_selection_accuracy']:.3f}  "
        f"first_tool_accuracy={report['first_tool_accuracy']:.3f}  "
        f"tool_success_rate={report['tool_success_rate']:.3f}  "
        f"source_rate={report['source_rate']:.3f}"
    )


if __name__ == "__main__":
    main()
