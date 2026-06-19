# WisdomSystem - 智扫通智能客服系统

基于 **LangChain + LangGraph** 构建的企业级智能客服系统，支持高级 RAG 检索、四层记忆库和断点续聊功能。

---

## 🚀 功能特性

### 🔍 高级 RAG 检索

| 技术 | 说明 | 效果 |
|------|------|------|
| **Contextual Retrieval** | 为每个 chunk 添加上下文描述（章节、主题、摘要），解决孤立chunk丢失文档上下文的问题 | Recall@5 提升至 90% |
| **Query 改写** | 三路改写：同义替换版、句式转换版、意图补全版 | 覆盖口语化/刁钻提问 |
| **语义校验** | 确保改写后的 Query 与原问题语义相似度 ≥ 0.8，避免偏离意图 | 过滤无效改写 |
| **快速相似度预过滤** | 使用字符重叠率、长度比率、关键词重叠快速过滤低相似度文本 | 减少API调用次数 |
| **BM25 混合召回** | 结合向量语义检索与 BM25 关键词匹配，使用 jieba 中文分词 | 兼顾语义和关键词 |
| **RRF 融合** | Reciprocal Rank Fusion 算法融合多源检索结果 | 优化排序结果 |
| **Rerank 精排** | 基于语义相似度的最终排序，支持批量嵌入计算 | 过滤无关文档 |

**检索流程**：
```
用户提问 → 三路 Query 改写 → 语义校验过滤 → 向量检索 + BM25 检索 → RRF 融合 → Rerank 精排 → 返回 Top-5 文档
```

### 🧠 四层记忆库

| 层级 | 类型 | 存储方式 | 用途 |
|------|------|---------|------|
| Layer 1 | 当前上下文 | 截断式 | 短期对话上下文 |
| Layer 2 | 用户档案 | SQLite | 用户姓名、职业、偏好等结构化信息 |
| Layer 3 | 近期摘要 | SQLite/Redis | 轻量级关键词提取 |
| Layer 4 | 长期经验 | RAG 向量库 | 成功案例、失败尝试 |

### 💬 断点续聊

- 支持会话持久化存储（文件 + Redis）
- 跨会话记忆恢复，自动加载最近历史会话
- 用户画像自动更新
- 历史记录自动保存和加载

### ⚡ 性能优化

| 优化项 | 效果 |
|--------|------|
| **单例模式** | 所有核心组件采用单例模式，避免重复初始化 |
| **懒加载模型** | 启动时间优化 |
| **Redis 缓存** | RAG 结果缓存，默认 24 小时过期 |
| **Query 缓存** | 缓存命中时响应时间显著降低 |
| **系统消息优化** | 修复多系统消息冲突问题 |

---

## 📊 RAG 评估结果

| 指标 | 结果 |
|------|------|
| **Recall@1** | 58.0% |
| **Recall@3** | 88.0% |
| **Recall@5** | 90.0% |
| **MRR** | 0.712 |
| **忠诚度** | 100% |

测试用例：50 个真实用户刁钻提问（口语化、简短、不标准）

---

## 🛠️ 技术栈

| 模块 | 技术 | 版本 |
|------|------|------|
| **框架** | LangChain | 0.3.7 |
| **工作流** | LangGraph | 0.2.50 |
| **向量数据库** | ChromaDB | 0.5.15 |
| **前端** | Streamlit | 1.40.1 |
| **LLM** | 通义千问 (DashScope) | - |
| **缓存** | Redis / SimpleCache | - |
| **数据库** | SQLite | - |

---

## 📁 项目结构

```
WisdomSystem/
├── agent/                  # ReAct Agent 核心
│   ├── tools/              # 工具定义
│   │   ├── agent_tools.py  # 业务工具（RAG检索、天气查询等）
│   │   └── middleware.py   # 中间件（日志、提示词注入）
│   └── react_agent.py      # ReAct Agent 实现（流式输出）
├── rag/                    # RAG 检索模块
│   ├── contextual_enhancer.py  # Contextual Retrieval（上下文增强）
│   ├── question_splitter.py    # 按问题切分文档
│   ├── query_rewriter.py       # Query 改写（三路改写 + 语义校验）
│   ├── semantic_checker.py     # 语义相似度校验
│   ├── bm25_retriever.py       # BM25 检索
│   ├── rrf_fusion.py           # RRF 融合算法
│   ├── reranker.py             # Rerank 精排
│   ├── vector_store.py         # 向量存储
│   └── rag_service.py          # RAG 服务入口
├── memory/                 # 记忆管理
│   ├── layers.py           # 四层记忆定义
│   ├── memory_manager.py   # 记忆管理器（单例模式）
│   └── session_manager.py  # 会话管理
├── database/               # 数据库模块
│   ├── sqlite_db.py        # SQLite 数据存储（单例模式）
│   └── redis_cache.py      # Redis 缓存（单例模式，降级到内存缓存）
├── model/                  # 模型工厂
│   └── factory.py          # 通义千问模型初始化
├── config/                 # 配置文件
│   ├── agent.yml           # Agent 配置
│   ├── chroma.yml          # 向量库配置
│   ├── rag.yml             # RAG 配置
│   └── prompts.yml         # 提示词配置
├── prompts/                # 提示词模板
│   ├── main_prompt.txt     # 主提示词
│   ├── rag_summarize.txt   # RAG 总结提示词
│   └── report_prompt.txt   # 报告生成提示词
├── data/                   # 知识库文档
│   ├── external/           # 外部数据
│   │   └── records.csv     # 用户使用记录
│   ├── 扫地机器人100问.pdf
│   ├── 扫地机器人100问2.txt
│   ├── 扫拖一体机器人100问.txt
│   ├── 故障排除.txt
│   ├── 维护保养.txt
│   └── 选购指南.txt
├── tests/                  # 测试模块
│   ├── rag_evaluation.py   # RAG 评估脚本
│   └── test_cases.json     # 测试用例（50个）
├── utils/                  # 工具函数
│   ├── config_handler.py   # 配置加载
│   ├── prompt_loader.py    # 提示词加载
│   ├── logger_handler.py   # 日志处理
│   └── path_tool.py        # 路径工具
├── app.py                  # Streamlit 前端入口
├── requirements.txt        # 依赖清单
├── .env                    # 环境变量配置（需自行配置）
├── AGENTS.md               # Agent 系统设计文档
└── README.md               # 项目说明文档
```

---

## 🔧 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/wwy2900/wisdomsystem.git
cd wisdomsystem
```

### 2. 创建虚拟环境

```bash
# 使用 conda（推荐）
conda create -n wisdomsystem-py311 python=3.11
conda activate wisdomsystem-py311

# 或使用 venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

创建并编辑 `.env` 文件：

```bash
# Windows: 使用记事本或 IDE 打开
notepad .env

# Linux/Mac: 使用编辑器
nano .env
```

`.env` 文件内容：
```env
# 通义千问 API 密钥（必填）
DASHSCOPE_API_KEY=your_api_key_here

# Redis 配置（可选，不配置则使用内存缓存）
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

**获取 API Key**：
1. 访问 [阿里云 DashScope 控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 创建 API Key（免费额度：100万 Token/月）

### 5. Redis 配置（可选）

Redis 用于缓存和会话管理，不配置则自动降级到内存缓存。

**Windows 安装 Redis**：
1. 下载 Redis：https://github.com/tporadowski/redis/releases
2. 解压到 `D:\Redis`
3. 运行：`D:\Redis\redis-server.exe redis.windows.conf`
4. 验证：`D:\Redis\redis-cli.exe ping`（返回 PONG 表示成功）

**Docker 安装 Redis**：
```bash
docker run -d -p 6379:6379 redis
```

### 6. 运行应用

```bash
# 启动 Streamlit 前端
streamlit run app.py
```

访问 **http://localhost:8501** 即可使用。

### 7. 首次运行说明

首次运行时，系统会自动执行以下操作：
1. **加载知识库文档**：从 `data/` 目录读取所有文档
2. **切分文档**：使用 `QuestionBasedSplitter` 按问题切分
3. **上下文增强**：为每个 chunk 添加上下文描述
4. **构建向量库**：将文档向量存储到 ChromaDB（`chroma_db/` 目录）

**首次运行时间**：约 5-10 分钟（取决于文档数量和网络速度）

---

## 🧪 RAG 评估

运行 RAG 评估脚本测试召回率和忠诚度：

```bash
python tests/rag_evaluation.py
```

评估指标：
- **召回率**: 测试用例能否正确检索到相关文档（Recall@1/3/5）
- **MRR**: 平均倒数排名，衡量检索精度
- **忠诚度**: 回答是否基于检索到的文档，无幻觉

评估结果会保存到 `rag_evaluation_results.json`。

---

## 🔗 知识库文档

项目内置扫地机器人相关知识库：
- 产品问答（100问 × 3）
- 故障排除指南
- 维护保养建议
- 选购指南

---

## 📝 配置说明

### agent.yml

```yaml
agent_name: WisdomAgent
max_iterations: 10
temperature: 0.7
external_data_path: data/external/records.csv
```

### rag.yml

```yaml
chat_model_name: qwen-max
embedding_model_name: text-embedding-v3
similarity_threshold: 0.8
top_k: 5
```

### chroma.yml

```yaml
persist_directory: ./chroma_db
collection_name: knowledge_base
k: 10
```

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目地址**：https://github.com/wwy2900/wisdomsystem

**文档说明**：
- `AGENTS.md` - Agent 系统设计文档，包含架构说明和扩展指南
