"""Export vector store chunks to a snapshot for labeling and heuristic prefill."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from eval.eval_utils import ensure_report_dir, save_json
from rag.vector_store import VectorStoreService


def _write_chunks_md(path: Path, chunks: list[dict]) -> None:
    lines = ["# Chunk Snapshot", ""]
    for chunk in chunks:
        doc_id = chunk.get("doc_id", "")
        content = chunk.get("content", "") or ""
        metadata = chunk.get("metadata") or {}
        lines.append(f"## {doc_id}")
        lines.append("")
        lines.append(f"- source_file: {metadata.get('source_file', '')}")
        lines.append(f"- user_id: {metadata.get('user_id', '')}")
        lines.append(f"- page: {metadata.get('page', '')}")
        lines.append(f"- section: {metadata.get('section_title', '') or metadata.get('section_path', '')}")
        lines.append("")
        preview = content[:500]
        lines.append("```text")
        lines.append(preview)
        lines.append("```")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def export_chunks(limit: int = 1000, offset: int = 0, user_id: str | None = None) -> dict:
    service = VectorStoreService()
    result = service.list_chunks(limit=limit, offset=offset, user_id=user_id)
    chunks = result.get("chunks", [])

    report_dir = ensure_report_dir()
    json_path = report_dir / "chunks_snapshot.json"
    md_path = report_dir / "chunks_snapshot.md"

    save_json(json_path, result)
    _write_chunks_md(md_path, chunks)

    print(f"[export_chunks] exported {len(chunks)} chunks (total={result.get('total', 0)})")
    print(f"[export_chunks] JSON: {json_path}")
    print(f"[export_chunks] MD:   {md_path}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Export vector store chunks snapshot")
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--user-id", dest="user_id", default=None)
    args = parser.parse_args()

    try:
        export_chunks(limit=args.limit, offset=args.offset, user_id=args.user_id)
    except Exception as exc:
        print(f"[export_chunks] ERROR: {exc}")
        report_dir = ensure_report_dir()
        save_json(
            report_dir / "chunks_snapshot.json",
            {"total": 0, "limit": args.limit, "offset": args.offset, "chunks": [], "error": str(exc)},
        )


if __name__ == "__main__":
    main()
