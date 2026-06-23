# wisdomsystem 量化评测框架

本目录提供覆盖 RAG 检索、回答生成、Agent 工具选择和 SSE 流式性能的量化评测脚本。

## 评测目标

| 评测类型 | 脚本 | 核心指标 |
|---|---|---|
| RAG 检索评测 | `evaluate_retrieval.py` | Recall@1/3/5、MRR |
| RAG 生成评测 | `evaluate_answer.py` | Keyword Coverage、Citation Rate、Answer Pass Rate、No-answer Accuracy |
| Agent 工具评测 | `evaluate_agent.py` | Tool Selection Accuracy、First Tool Accuracy、Tool Success Rate、Source Rate |
| 流式性能评测 | `benchmark_stream.py` | TTFT、Total Latency、P50/P95 |

## 数据集格式

### rag_cases.jsonl

```json
{
  "id": "rag_001",
  "category": "知识库问答",
  "user_id": "__shared__",
  "query": "咋充电",
  "expected_doc_ids": ["chunk_xxx"],
  "expected_keywords": ["充电", "充电座", "电源适配器"],
  "must_cite": true,
  "label_status": "heuristic",
  "note": "口语化简短提问"
}
```

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | 样本 ID |
| `category` | 是 | 场景类别 |
| `user_id` | 否 | 默认 `__shared__` |
| `query` | 是 | 用户问题 |
| `expected_doc_ids` | 是 | 期望召回的 chunk ID；空数组时检索评测跳过 |
| `expected_keywords` | 是 | 回答应覆盖的关键词 |
| `must_cite` | 否 | 是否要求返回 sources，默认 true |
| `label_status` | 是 | `labeled` / `heuristic` / `need_label` |

### agent_cases.jsonl

```json
{"id":"agent_001","category":"设备信息","user_id":"user_xxx","query":"我的设备保修到什么时候","expected_tool":"lookup_user_devices","expected_keywords":["保修","设备"],"note":"应查询当前用户绑定设备"}
```

### no_answer_cases.jsonl

```json
{"id":"na_001","query":"这台机器人能不能在火星表面建图","expected_behavior":"refuse_or_clarify","forbidden_keywords":["肯定可以","一定支持"],"note":"知识库无答案，应避免编造"}
```

## 运行流程

```bash
# 1. 从旧测试集迁移（自动启发式预填 expected_doc_ids）
python eval/migrate_test_cases.py

# 2. 导出知识库 chunk 快照（供标注参考）
python eval/export_chunks.py --limit 1000

# 3. RAG 检索评测
python eval/evaluate_retrieval.py

# 4. RAG 生成评测
python eval/evaluate_answer.py

# 5. Agent 工具评测
python eval/evaluate_agent.py

# 6. SSE 流式性能评测（service 模式）
python eval/benchmark_stream.py --mode service

# 6b. SSE 流式性能评测（http 模式，需先启动 FastAPI）
python eval/benchmark_stream.py --mode http --base-url http://127.0.0.1:8000

# 7. 生成 Markdown 报告
python eval/generate_markdown_report.py
```

## 指标解释

### RAG 检索

| 指标 | 定义 |
|---|---|
| Recall@K | 前 K 个召回结果中命中期望文档的样本比例 |
| MRR | 第一个命中文档排名倒数的平均值 |

### RAG 生成

| 指标 | 定义 |
|---|---|
| Keyword Coverage | 命中 expected_keywords 数量 / 总数 |
| Citation Rate | 返回 sources 的样本比例 |
| Answer Pass Rate | coverage >= 0.6 且 citation_ok 且非空 |
| No-answer Accuracy | 无禁用关键词且表达拒绝/澄清 |

### Agent 工具

| 指标 | 定义 |
|---|---|
| Tool Selection Accuracy | 期望工具出现在调用列表中的样本比例 |
| First Tool Accuracy | 第一个工具即期望工具的样本比例 |
| Tool Success Rate | 有 TOOL_RESULT 且无 error 的比例 |
| Source Rate | 最终有 sources 的样本比例 |

### 流式性能

| 指标 | 定义 |
|---|---|
| TTFT | Time To First Token（首字延迟） |
| Total Latency | 总耗时 |
| P50 / P95 | 中位数 / 95 分位 |

## 检索模式

| mode | 实现 |
|---|---|
| `vector_only` | `VectorStoreService.retrieve_documents` |
| `bm25_only` | `BM25Retriever.retrieve` |
| `hybrid_rerank` | `RagSummarizeService.retriever_docs`（完整 RAG 链路） |

## 注意事项

- `expected_doc_ids` 当前为启发式预填（`label_status=heuristic`），非人工标注，Recall/MRR 仅供参考。
- Agent 评测通过 `ChatService.chat_stream` 调用（客服工具依赖请求上下文）。
- 无 `DASHSCOPE_API_KEY` 时，生成评测和 Agent 评测会优雅降级，输出空报告。
- http 模式需先启动 `uvicorn api.main:app --host 0.0.0.0 --port 8000`。
- 所有报告输出到 `eval/reports/`，Markdown 报告输出到 `docs/evaluation_report.md`。
