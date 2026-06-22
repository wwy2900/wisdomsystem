# WisdomSystem - 智扫通智能客服

基于 `LangChain + LangGraph + FastAPI + Streamlit` 的企业级智能客服项目。当前版本重点落在统一前后端架构、私有知识隔离、多格式知识入库、结构化 PDF 解析，以及知识库管理链路的稳定性重构。

---

## 核心能力

### 1. 统一前后端架构

- Streamlit 仅作为前端客户端
- FastAPI 作为唯一业务入口
- 聊天通过 HTTP + SSE 调用后端
- 知识库、会话、流式问答统一走 API

### 2. RAG 检索链路

- Query Rewrite
- 向量检索 + BM25 混合召回
- RRF 融合
- Rerank 精排
- 共享知识库 + 当前用户私有知识联合检索

### 3. 私有知识库隔离

- 上传、检索、删除、列表查询均支持 `user_id`
- RAG 只允许命中共享知识和当前用户私有知识
- 缓存按用户作用域隔离
- 同内容文件允许不同用户分别建立私有知识

### 4. 多格式文档解析与结构化入库

当前支持：

- `txt`
- `pdf`
- `docx`
- `xlsx`
- `csv`
- `md`
- `json`

解析策略：

- `csv/xlsx` 按行拆成结构化 `Document`
- `json` 按顶层记录或键拆分
- `md` 按标题层级拆分
- `docx` 按节和表格线性提取
- `pdf` 使用 Docling 输出“页内 section 文本块 + 独立 table 文档”

### 5. PDF OCR 自动兜底

- 使用 `Docling + OcrAutoOptions`
- 仅对扫描页或大面积位图区域自动兜底
- 不强制整页 OCR
- 保留 `page / section_path / section_title / content_type / table_index`
- OCR metadata 包含：
  - `ocr_enabled`
  - `ocr_mode=auto_fallback`
  - `ocr_bitmap_area_threshold=0.05`

### 6. 知识库稳定性改造

- `doc_id` 改为稳定唯一 ID，不再依赖顺序号
- MD5 记录改为结构化原子写入
- 上传、删除、重建后自动失效 BM25 / RAG 缓存
- chunk 分页和过滤改为底层分页查询，不再全量扫描后再切片

---

## 当前版本重点

### v1.6

- 新增 `DocumentParserFactory`，统一 `txt/pdf/docx/xlsx/csv/md/json` 解析入口
- PDF 解析升级为 Docling 结构化 Markdown + OCR 自动兜底
- BM25 增加上传、删除、重建后的刷新机制
- 知识库 chunk ID 升级为稳定唯一 ID
- 知识库列表与删除链路改为分页查询和公开 API 访问
- 补充依赖兼容说明与回归测试

详细记录见 [CHANGELOG.md](CHANGELOG.md)。

---

## 项目结构

```text
WisdomSystem/
├── agent/                  # ReAct Agent 与工具
├── api/                    # FastAPI 入口与路由
├── database/               # Redis / SQLite / 缓存封装
├── frontend/               # Streamlit -> FastAPI 客户端
├── memory/                 # 四层记忆与会话管理
├── rag/                    # 检索、解析器、向量库、BM25
├── services/               # 聊天与知识库服务
├── data/                   # 数据文件与上传目录
├── tests/                  # 测试与评估脚本
├── DEPENDENCY_COMPATIBILITY.md
├── AGENTS.md
├── CHANGELOG.md
└── app.py
```

---

## 环境要求

- Python 3.11
- 推荐 Conda 环境：`wisdomsystem-py311`
- 可选 Redis
- DashScope API Key

---

## 安装与启动

### 1. 克隆项目

```bash
git clone https://github.com/wwy2900/wisdomsystem.git
cd wisdomsystem
```

### 2. 创建环境

```bash
conda create -n wisdomsystem-py311 python=3.11
conda activate wisdomsystem-py311
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 `.env`

```env
DASHSCOPE_API_KEY=your_api_key_here
FASTAPI_API_KEY=your_fastapi_api_key

REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_CONNECT_TIMEOUT=1
REDIS_SOCKET_TIMEOUT=1
```

### 5. 启动服务

先启动 Redis（可选）：

```bash
D:\Redis\redis-server.exe
```

再启动 FastAPI：

```bash
conda activate wisdomsystem-py311
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

最后启动 Streamlit：

```bash
conda activate wisdomsystem-py311
streamlit run app.py --server.port 8501
```

访问地址：

```text
FastAPI Docs: http://localhost:8000/docs
Streamlit:    http://localhost:8501
```

---

## 主要接口

### 聊天与会话

- `GET /health`
- `POST /api/v1/sessions`
- `GET /api/v1/users/{user_id}/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`

### 知识库管理

- `POST /api/v1/knowledge/documents/upload`
  - 支持 `txt/pdf/docx/xlsx/csv/md/json`
- `GET /api/v1/knowledge/chunks`
- `GET /api/v1/knowledge/search`
- `GET /api/v1/knowledge/users/{user_id}/chunks`
- `DELETE /api/v1/knowledge/chunks/{doc_id}`
- `POST /api/v1/knowledge/rebuild`

---

## 常用验证命令

语法检查：

```bash
conda activate wisdomsystem-py311
python -m compileall agent memory rag database utils model api services frontend app.py tests
```

解析器测试：

```bash
conda activate wisdomsystem-py311
python -m unittest tests.test_document_parsers -v
python -m unittest tests.test_rag_stability -v
```

依赖一致性：

```bash
conda activate wisdomsystem-py311
python -m pip check
```

RAG 评估：

```bash
conda activate wisdomsystem-py311
python tests/rag_evaluation.py
```

---

## 维护要点

- Streamlit 前端只能通过 `frontend/api_client.py` 调用 FastAPI
- 不要在前端直接导入 Agent、服务层或向量库
- 私有知识改动必须保持严格用户隔离
- 删除 chunk 只删向量库记录，不删除原始上传文件
- 重建索引会清空当前向量库，执行前必须明确提示
- OCR 当前保留 Auto fallback，不承诺强制语言控制
- 依赖升级前先核对 [DEPENDENCY_COMPATIBILITY.md](DEPENDENCY_COMPATIBILITY.md)

更多维护信息见 [AGENTS.md](AGENTS.md)。
