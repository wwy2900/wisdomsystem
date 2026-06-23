"""RAG answer evaluation: Keyword Coverage, Citation Rate, Answer Pass Rate, No-answer Accuracy."""
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
    has_forbidden_keyword,
    is_refusal_or_clarify,
    keyword_coverage,
    load_jsonl,
    save_json,
)

DEFAULT_RAG_CASES = EVAL_DIR / "rag_cases.jsonl"
DEFAULT_NO_ANSWER_CASES = EVAL_DIR / "no_answer_cases.jsonl"


def _sources_to_dicts(sources) -> list[dict]:
    result = []
    for src in sources or []:
        if hasattr(src, "to_dict"):
            result.append(src.to_dict())
        elif isinstance(src, dict):
            result.append(src)
    return result


def evaluate_rag_answers(cases: list[dict]) -> dict:
    from rag.rag_service import RagSummarizeService

    service = RagSummarizeService()
    details: list[dict] = []
    coverage_sum = 0.0
    citation_count = 0
    pass_count = 0

    for case in cases:
        query = case["query"]
        keywords = case.get("expected_keywords", []) or []
        must_cite = case.get("must_cite", True)
        user_id = case.get("user_id")
        uid = user_id if user_id and user_id != "__shared__" else None

        try:
            answer, sources = service.rag_summarize_with_sources(query, user_id=uid)
        except Exception as exc:
            details.append(
                {
                    "id": case.get("id", ""),
                    "query": query,
                    "answer": "",
                    "sources": [],
                    "keyword_coverage": 0.0,
                    "citation_ok": False,
                    "passed": False,
                    "error": str(exc),
                }
            )
            continue

        cov = keyword_coverage(answer, keywords)
        citation_ok = (len(sources) > 0) or (not must_cite)
        non_empty = bool(answer and answer.strip())
        passed = cov >= 0.6 and citation_ok and non_empty

        coverage_sum += cov
        if citation_ok:
            citation_count += 1
        if passed:
            pass_count += 1

        details.append(
            {
                "id": case.get("id", ""),
                "query": query,
                "answer": answer[:300],
                "sources": _sources_to_dicts(sources),
                "keyword_coverage": round(cov, 4),
                "citation_ok": citation_ok,
                "passed": passed,
            }
        )

    total = len(details)
    return {
        "total": total,
        "avg_keyword_coverage": round(coverage_sum / total, 4) if total else 0.0,
        "citation_rate": round(citation_count / total, 4) if total else 0.0,
        "answer_pass_rate": round(pass_count / total, 4) if total else 0.0,
        "details": details,
    }


def evaluate_no_answer(cases: list[dict]) -> dict:
    from rag.rag_service import RagSummarizeService

    service = RagSummarizeService()
    details: list[dict] = []
    pass_count = 0

    for case in cases:
        query = case["query"]
        forbidden = case.get("forbidden_keywords", []) or []

        try:
            answer, _sources = service.rag_summarize_with_sources(query)
        except Exception as exc:
            details.append(
                {
                    "id": case.get("id", ""),
                    "query": query,
                    "answer": "",
                    "no_forbidden": False,
                    "is_refusal": False,
                    "passed": False,
                    "error": str(exc),
                }
            )
            continue

        no_forbidden = not has_forbidden_keyword(answer, forbidden)
        refusal = is_refusal_or_clarify(answer)
        passed = no_forbidden and refusal
        if passed:
            pass_count += 1

        details.append(
            {
                "id": case.get("id", ""),
                "query": query,
                "answer": answer[:300],
                "no_forbidden": no_forbidden,
                "is_refusal": refusal,
                "passed": passed,
            }
        )

    total = len(details)
    return {
        "total": total,
        "no_answer_accuracy": round(pass_count / total, 4) if total else 0.0,
        "details": details,
    }


def evaluate(
    rag_cases_path: str | Path = DEFAULT_RAG_CASES,
    no_answer_cases_path: str | Path = DEFAULT_NO_ANSWER_CASES,
) -> dict:
    rag_cases = load_jsonl(rag_cases_path) if Path(rag_cases_path).exists() else []
    no_answer_cases = load_jsonl(no_answer_cases_path) if Path(no_answer_cases_path).exists() else []

    report: dict = {
        "rag_cases_path": str(rag_cases_path),
        "no_answer_cases_path": str(no_answer_cases_path),
    }

    if rag_cases:
        print(f"[evaluate_answer] evaluating {len(rag_cases)} RAG cases ...")
        rag_result = evaluate_rag_answers(rag_cases)
        report["rag"] = rag_result
        print(
            f"  avg_keyword_coverage={rag_result['avg_keyword_coverage']:.3f}  "
            f"citation_rate={rag_result['citation_rate']:.3f}  "
            f"answer_pass_rate={rag_result['answer_pass_rate']:.3f}"
        )
    else:
        report["rag"] = {"total": 0, "avg_keyword_coverage": 0.0, "citation_rate": 0.0, "answer_pass_rate": 0.0, "details": []}
        print("[evaluate_answer] no RAG cases found, skipping.")

    if no_answer_cases:
        print(f"[evaluate_answer] evaluating {len(no_answer_cases)} no-answer cases ...")
        na_result = evaluate_no_answer(no_answer_cases)
        report["no_answer"] = na_result
        print(f"  no_answer_accuracy={na_result['no_answer_accuracy']:.3f}")
    else:
        report["no_answer"] = {"total": 0, "no_answer_accuracy": 0.0, "details": []}
        print("[evaluate_answer] no no-answer cases found, skipping.")

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG answer evaluation")
    parser.add_argument("--rag-cases", default=str(DEFAULT_RAG_CASES))
    parser.add_argument("--no-answer-cases", default=str(DEFAULT_NO_ANSWER_CASES))
    args = parser.parse_args()

    report = evaluate(rag_cases_path=args.rag_cases, no_answer_cases_path=args.no_answer_cases)
    out_path = ensure_report_dir() / "answer_report.json"
    save_json(out_path, report)
    print(f"[evaluate_answer] report saved to {out_path}")


if __name__ == "__main__":
    main()
