"""RAG retrieval evaluation: Recall@K and MRR across multiple retrieval modes."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from eval.eval_utils import EVAL_DIR, ensure_report_dir, load_jsonl, save_json

DEFAULT_CASES = EVAL_DIR / "rag_cases.jsonl"
DEFAULT_K = 5


def _retrieve_vector_only(query: str, k: int, user_id: str | None):
    from rag.vector_store import VectorStoreService

    service = VectorStoreService()
    uid = user_id if user_id and user_id != "__shared__" else None
    return service.retrieve_documents(query, k=k, user_id=uid)


def _retrieve_bm25_only(query: str, k: int, user_id: str | None):
    from rag.bm25_retriever import BM25Retriever

    retriever = BM25Retriever()
    uid = user_id if user_id and user_id != "__shared__" else None
    return retriever.retrieve(query, k=k, user_id=uid)


def _retrieve_hybrid_rerank(query: str, k: int, user_id: str | None):
    from rag.rag_service import RagSummarizeService

    service = RagSummarizeService()
    uid = user_id if user_id and user_id != "__shared__" else None
    docs = service.retriever_docs(query, user_id=uid)
    return docs[:k]


_MODES = {
    "vector_only": _retrieve_vector_only,
    "bm25_only": _retrieve_bm25_only,
    "hybrid_rerank": _retrieve_hybrid_rerank,
}


def _doc_id(doc) -> str:
    metadata = getattr(doc, "metadata", None) or {}
    return str(metadata.get("doc_id", ""))


def _evaluate_mode(cases: list[dict], mode: str, retrieve_fn, k: int) -> dict:
    details: list[dict] = []
    hit_1 = hit_3 = hit_5 = 0
    mrr_sum = 0.0
    count = 0

    for case in cases:
        expected = case.get("expected_doc_ids") or []
        if not expected:
            continue
        count += 1
        query = case["query"]
        user_id = case.get("user_id")

        try:
            docs = retrieve_fn(query, k, user_id)
        except Exception as exc:
            details.append(
                {
                    "id": case["id"],
                    "category": case.get("category", ""),
                    "query": query,
                    "expected_doc_ids": expected,
                    "retrieved_doc_ids": [],
                    "hit_at_1": False,
                    "hit_at_3": False,
                    "hit_at_5": False,
                    "rank": None,
                    "mrr": 0.0,
                    "error": str(exc),
                }
            )
            continue

        retrieved_ids = [_doc_id(d) for d in docs[:k]]
        h1 = any(did in expected for did in retrieved_ids[:1])
        h3 = any(did in expected for did in retrieved_ids[:3])
        h5 = any(did in expected for did in retrieved_ids[:5])

        rank = None
        mrr = 0.0
        for idx, did in enumerate(retrieved_ids):
            if did in expected:
                rank = idx + 1
                mrr = 1.0 / rank
                break

        if h1:
            hit_1 += 1
        if h3:
            hit_3 += 1
        if h5:
            hit_5 += 1
        mrr_sum += mrr

        details.append(
            {
                "id": case["id"],
                "category": case.get("category", ""),
                "query": query,
                "expected_doc_ids": expected,
                "retrieved_doc_ids": retrieved_ids,
                "hit_at_1": h1,
                "hit_at_3": h3,
                "hit_at_5": h5,
                "rank": rank,
                "mrr": mrr,
            }
        )

    return {
        "recall_at_1": hit_1 / count if count else 0.0,
        "recall_at_3": hit_3 / count if count else 0.0,
        "recall_at_5": hit_5 / count if count else 0.0,
        "mrr": mrr_sum / count if count else 0.0,
        "labeled_count": count,
        "details": details,
    }


def evaluate(
    cases_path: str | Path = DEFAULT_CASES,
    k: int = DEFAULT_K,
    modes: list[str] | None = None,
) -> dict:
    cases = load_jsonl(cases_path)
    labeled = [c for c in cases if c.get("expected_doc_ids")]
    skipped = len(cases) - len(labeled)

    selected_modes = modes or list(_MODES.keys())

    report = {
        "dataset": str(cases_path),
        "total_case_count": len(cases),
        "labeled_case_count": len(labeled),
        "skipped_unlabeled_count": skipped,
        "k": k,
        "modes": {},
    }

    if not labeled:
        print("[evaluate_retrieval] No labeled cases found. Please fill expected_doc_ids first.")
        for mode in selected_modes:
            report["modes"][mode] = {
                "recall_at_1": 0.0,
                "recall_at_3": 0.0,
                "recall_at_5": 0.0,
                "mrr": 0.0,
                "labeled_count": 0,
                "details": [],
            }
        return report

    for mode in selected_modes:
        retrieve_fn = _MODES[mode]
        print(f"[evaluate_retrieval] evaluating mode: {mode} ...")
        try:
            result = _evaluate_mode(labeled, mode, retrieve_fn, k)
        except Exception as exc:
            print(f"[evaluate_retrieval] mode {mode} failed: {exc}")
            result = {
                "recall_at_1": 0.0,
                "recall_at_3": 0.0,
                "recall_at_5": 0.0,
                "mrr": 0.0,
                "labeled_count": len(labeled),
                "details": [],
                "error": str(exc),
            }
        report["modes"][mode] = result
        print(
            f"  Recall@1={result['recall_at_1']:.3f}  "
            f"Recall@3={result['recall_at_3']:.3f}  "
            f"Recall@5={result['recall_at_5']:.3f}  "
            f"MRR={result['mrr']:.3f}"
        )

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG retrieval evaluation")
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--k", type=int, default=DEFAULT_K)
    parser.add_argument(
        "--modes",
        nargs="+",
        default=None,
        help="Retrieval modes to evaluate (e.g. vector_only bm25_only hybrid_rerank). Default: all.",
    )
    args = parser.parse_args()

    report = evaluate(cases_path=args.cases, k=args.k, modes=args.modes)
    out_path = ensure_report_dir() / "retrieval_report.json"
    save_json(out_path, report)
    print(f"[evaluate_retrieval] report saved to {out_path}")


if __name__ == "__main__":
    main()
