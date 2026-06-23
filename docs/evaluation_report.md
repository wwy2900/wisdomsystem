# wisdomsystem 量化评测报告

> 生成时间: 自动生成（基于 eval/reports/*.json）

## 1. 评测目标

本评测用于验证 wisdomsystem 在智能客服场景下的 RAG 检索、回答生成、Agent 工具选择和 SSE 流式响应能力。

## 2. 评测数据集

| 数据集 | 样本数 | 说明 |
|---|---:|---|
| rag_cases.jsonl | 50 | 覆盖口语化短问句、故障排查、功能咨询、耗材维护 |
| agent_cases.jsonl | 0 | 覆盖设备、耗材、售后政策、服务渠道、知识库问答 |
| no_answer_cases.jsonl | 0 | 验证无答案时是否避免编造 |

> 注意: `expected_doc_ids` 当前为基于关键词重叠的启发式预填（`label_status=heuristic`），非人工标注，Recall/MRR 指标仅供参考。

## 3. RAG 检索评测

- 数据集: `D:\projects\wisdomsystem-main\eval\rag_cases.jsonl`
- 总样本数: 50
- 已标注样本数: 50
- 跳过未标注样本数: 0
- K 值: 5

| 方法 | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| vector_only | 0.4000 | 0.6600 | 0.7400 | 0.5313 |
| bm25_only | N/A | N/A | N/A | N/A |
| hybrid_rerank | 0.4000 | 0.6600 | 0.7400 | 0.5313 |

### 失败案例（Top-5 未命中）

- **rag_001**: 咋充电
  - 期望: `['chunk_0301', 'chunk_0302', 'chunk_0337']`
  - 实际: `['chunk_0103', 'chunk_0104', 'chunk_0197', 'chunk_0108', 'chunk_0035']`
- **rag_004**: 拖地效果怎么样
  - 期望: `['chunk_0208', 'chunk_0115', 'chunk_0131']`
  - 实际: `['chunk_0064', 'chunk_0016', 'chunk_0119', 'chunk_0018', 'chunk_0203']`
- **rag_009**: 能爬地毯吗
  - 期望: `['chunk_0355', 'chunk_0011', 'chunk_0255']`
  - 实际: `['chunk_0175', 'chunk_0153', 'chunk_0013', 'chunk_0064', 'chunk_0229']`
- **rag_011**: 边刷咋换
  - 期望: `['chunk_0345', 'chunk_0346', 'chunk_0348']`
  - 实际: `['chunk_0122', 'chunk_0121', 'chunk_0031', 'chunk_0067', 'chunk_0294']`
- **rag_022**: 续航多久
  - 期望: `['chunk_0126', 'chunk_0127', 'chunk_0179']`
  - 实际: `['chunk_0076', 'chunk_0121', 'chunk_0070', 'chunk_0071', 'chunk_0188']`

## 4. RAG 生成评测

该部分尚未运行评测，暂无结果。

## 5. Agent 工具调用评测

该部分尚未运行评测，暂无结果。

## 6. SSE 流式性能评测

该部分尚未运行评测，暂无结果。

## 7. 后续优化方向

1. 人工修正 `expected_doc_ids`，将 `label_status` 从 `heuristic` 改为 `labeled`。
2. 对比不同 chunk size 和 overlap 对检索效果的影响。
3. 增加 BM25-only 与 hybrid-no-rerank baseline 对比。
4. 引入 LLM-as-judge，但保留规则评测作为稳定基线。
5. 将评测报告接入 CI artifact。

## 8. 简历描述建议

- 构建了覆盖 RAG 检索、回答生成、Agent 工具选择、SSE 流式性能的量化评测体系。
- 实现 Recall@K、MRR、Keyword Coverage、Citation Rate、Tool Selection Accuracy、TTFT/P95 等指标。
- 评测框架支持 vector_only / bm25_only / hybrid_rerank 三种检索模式对比。
