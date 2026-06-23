"""Generate docs/evaluation_report.md from JSON reports."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from eval.eval_utils import EVAL_DIR, PROJECT_ROOT, REPORT_DIR

REPORT_FILES = {
    "retrieval": REPORT_DIR / "retrieval_report.json",
    "answer": REPORT_DIR / "answer_report.json",
    "agent": REPORT_DIR / "agent_report.json",
    "stream": REPORT_DIR / "stream_benchmark_report.json",
}

OUTPUT_PATH = PROJECT_ROOT / "docs" / "evaluation_report.md"


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "N/A"
    if isinstance(value, float):
        return f"{value:.4f}{suffix}"
    return f"{value}{suffix}"


def _render_retrieval(report: dict | None) -> list[str]:
    lines = ["## 3. RAG 检索评测", ""]
    if report is None:
        lines.append("该部分尚未运行评测，暂无结果。")
        lines.append("")
        return lines

    lines.append(f"- 数据集: `{report.get('dataset', 'N/A')}`")
    lines.append(f"- 总样本数: {report.get('total_case_count', 0)}")
    lines.append(f"- 已标注样本数: {report.get('labeled_case_count', 0)}")
    lines.append(f"- 跳过未标注样本数: {report.get('skipped_unlabeled_count', 0)}")
    lines.append(f"- K 值: {report.get('k', 5)}")
    lines.append("")
    lines.append("| 方法 | Recall@1 | Recall@3 | Recall@5 | MRR |")
    lines.append("|---|---:|---:|---:|---:|")

    modes = report.get("modes", {})
    for mode_name in ("vector_only", "bm25_only", "hybrid_rerank"):
        mode_data = modes.get(mode_name, {})
        lines.append(
            f"| {mode_name} | "
            f"{_fmt(mode_data.get('recall_at_1'))} | "
            f"{_fmt(mode_data.get('recall_at_3'))} | "
            f"{_fmt(mode_data.get('recall_at_5'))} | "
            f"{_fmt(mode_data.get('mrr'))} |"
        )
    lines.append("")

    details = []
    for mode_data in modes.values():
        for d in mode_data.get("details", []):
            if not d.get("hit_at_5") and not d.get("error"):
                details.append(d)
    if details:
        lines.append("### 失败案例（Top-5 未命中）")
        lines.append("")
        for d in details[:5]:
            lines.append(f"- **{d.get('id', '')}**: {d.get('query', '')}")
            lines.append(f"  - 期望: `{d.get('expected_doc_ids', [])}`")
            lines.append(f"  - 实际: `{d.get('retrieved_doc_ids', [])}`")
        lines.append("")

    return lines


def _render_answer(report: dict | None) -> list[str]:
    lines = ["## 4. RAG 生成评测", ""]
    if report is None:
        lines.append("该部分尚未运行评测，暂无结果。")
        lines.append("")
        return lines

    rag = report.get("rag", {})
    na = report.get("no_answer", {})

    lines.append("| 指标 | 结果 |")
    lines.append("|---|---:|")
    lines.append(f"| Keyword Coverage | {_fmt(rag.get('avg_keyword_coverage'))} |")
    lines.append(f"| Citation Rate | {_fmt(rag.get('citation_rate'))} |")
    lines.append(f"| Answer Pass Rate | {_fmt(rag.get('answer_pass_rate'))} |")
    lines.append(f"| No-answer Accuracy | {_fmt(na.get('no_answer_accuracy'))} |")
    lines.append("")
    lines.append(f"- RAG 样本数: {rag.get('total', 0)}")
    lines.append(f"- 无答案样本数: {na.get('total', 0)}")
    lines.append("")
    return lines


def _render_agent(report: dict | None) -> list[str]:
    lines = ["## 5. Agent 工具调用评测", ""]
    if report is None:
        lines.append("该部分尚未运行评测，暂无结果。")
        lines.append("")
        return lines

    lines.append("| 指标 | 结果 |")
    lines.append("|---|---:|")
    lines.append(f"| Tool Selection Accuracy | {_fmt(report.get('tool_selection_accuracy'))} |")
    lines.append(f"| First Tool Accuracy | {_fmt(report.get('first_tool_accuracy'))} |")
    lines.append(f"| Tool Success Rate | {_fmt(report.get('tool_success_rate'))} |")
    lines.append(f"| Source Rate | {_fmt(report.get('source_rate'))} |")
    lines.append("")
    lines.append(f"- 样本数: {report.get('total', 0)}")
    lines.append("")

    details = [d for d in report.get("details", []) if not d.get("passed")]
    if details:
        lines.append("### 失败案例")
        lines.append("")
        for d in details[:5]:
            lines.append(f"- **{d.get('id', '')}**: {d.get('query', '')}")
            lines.append(f"  - 期望工具: `{d.get('expected_tool', '')}`")
            lines.append(f"  - 实际调用: `{d.get('called_tools', [])}`")
            if d.get("error"):
                lines.append(f"  - 错误: {d['error']}")
        lines.append("")

    return lines


def _render_stream(report: dict | None) -> list[str]:
    lines = ["## 6. SSE 流式性能评测", ""]
    if report is None:
        lines.append("该部分尚未运行评测，暂无结果。")
        lines.append("")
        return lines

    lines.append("| 指标 | 结果 |")
    lines.append("|---|---:|")
    lines.append(f"| P50 TTFT | {_fmt(report.get('p50_ttft_ms'), ' ms')} |")
    lines.append(f"| P95 TTFT | {_fmt(report.get('p95_ttft_ms'), ' ms')} |")
    lines.append(f"| P50 Total Latency | {_fmt(report.get('p50_total_ms'), ' ms')} |")
    lines.append(f"| P95 Total Latency | {_fmt(report.get('p95_total_ms'), ' ms')} |")
    lines.append("")
    lines.append(f"- 模式: `{report.get('mode', 'N/A')}`")
    lines.append(f"- 样本数: {report.get('case_count', 0)}")
    lines.append("")
    return lines


def generate() -> None:
    retrieval = _load_json(REPORT_FILES["retrieval"])
    answer = _load_json(REPORT_FILES["answer"])
    agent = _load_json(REPORT_FILES["agent"])
    stream = _load_json(REPORT_FILES["stream"])

    rag_count = 0
    if retrieval:
        rag_count = retrieval.get("labeled_case_count", 0)
    agent_count = agent.get("total", 0) if agent else 0
    na_count = answer.get("no_answer", {}).get("total", 0) if answer else 0

    lines: list[str] = [
        "# wisdomsystem 量化评测报告",
        "",
        f"> 生成时间: 自动生成（基于 eval/reports/*.json）",
        "",
        "## 1. 评测目标",
        "",
        "本评测用于验证 wisdomsystem 在智能客服场景下的 RAG 检索、回答生成、Agent 工具选择和 SSE 流式响应能力。",
        "",
        "## 2. 评测数据集",
        "",
        "| 数据集 | 样本数 | 说明 |",
        "|---|---:|---|",
        f"| rag_cases.jsonl | {rag_count} | 覆盖口语化短问句、故障排查、功能咨询、耗材维护 |",
        f"| agent_cases.jsonl | {agent_count} | 覆盖设备、耗材、售后政策、服务渠道、知识库问答 |",
        f"| no_answer_cases.jsonl | {na_count} | 验证无答案时是否避免编造 |",
        "",
        "> 注意: `expected_doc_ids` 当前为基于关键词重叠的启发式预填（`label_status=heuristic`），非人工标注，Recall/MRR 指标仅供参考。",
        "",
    ]

    lines.extend(_render_retrieval(retrieval))
    lines.extend(_render_answer(answer))
    lines.extend(_render_agent(agent))
    lines.extend(_render_stream(stream))

    lines.extend(
        [
            "## 7. 后续优化方向",
            "",
            "1. 人工修正 `expected_doc_ids`，将 `label_status` 从 `heuristic` 改为 `labeled`。",
            "2. 对比不同 chunk size 和 overlap 对检索效果的影响。",
            "3. 增加 BM25-only 与 hybrid-no-rerank baseline 对比。",
            "4. 引入 LLM-as-judge，但保留规则评测作为稳定基线。",
            "5. 将评测报告接入 CI artifact。",
            "",
            "## 8. 简历描述建议",
            "",
            "- 构建了覆盖 RAG 检索、回答生成、Agent 工具选择、SSE 流式性能的量化评测体系。",
            "- 实现 Recall@K、MRR、Keyword Coverage、Citation Rate、Tool Selection Accuracy、TTFT/P95 等指标。",
            "- 评测框架支持 vector_only / bm25_only / hybrid_rerank 三种检索模式对比。",
            "",
        ]
    )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"[generate_markdown_report] report saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    generate()
