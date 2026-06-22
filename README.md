# WisdomSystem

`WisdomSystem` 是一个面向智能客服场景的 RAG 系统，当前架构为：

- `FastAPI` 作为唯一业务后端
- `Vue 3 + Vite + TypeScript` 作为浏览器前端
- `LangChain + LangGraph` 负责 Agent 推理
- `ChromaDB + BM25 + Rerank` 负责检索
- `SQLite + Redis/SimpleCache + JSON` 负责认证、会话和缓存

旧版 `Streamlit` 前端仍保留在仓库中作为回退入口，但主流程已经切换为 `web/` 下的 Vue3 SPA。

## 核心能力

- 聊天工作台：SSE 流式回答、工具过程展示、会话切换
- 私有知识隔离：当前登录用户仅能访问自己的私有 chunk 和自己的会话
- 管理员知识库：共享知识上传、chunk 分页查看、检索预览、按 `doc_id` 删除、索引重建
- 多格式入库：`txt`、`pdf`、`docx`、`xlsx`、`csv`、`md`、`json`
- PDF 结构化解析：`Docling + OcrAutoOptions`

## 目录结构

```text
agent/                  ReAct Agent 与工具
api/                    FastAPI 路由、鉴权、SSE
database/               Redis / SQLite 封装
memory/                 会话与长期记忆
rag/                    解析器、检索、向量库
services/               聊天、知识库、认证服务
frontend/               旧版 Streamlit 客户端（兼容保留）
web/                    新版 Vue3 前端
tests/                  Python 回归测试
```

## 环境要求

- Python 3.11
- 推荐 Conda 环境：`wisdomsystem-py311`
- Node.js 18+
- 可选 Redis
- DashScope API Key

## 后端安装

```bash
conda create -n wisdomsystem-py311 python=3.11
conda activate wisdomsystem-py311
pip install -r requirements.txt
```

## 前端安装

```bash
cd web
npm install
```

## `.env` 示例

```env
DASHSCOPE_API_KEY=your_dashscope_api_key
FASTAPI_API_KEY=legacy_fastapi_api_key

REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_CONNECT_TIMEOUT=1
REDIS_SOCKET_TIMEOUT=1

FRONTEND_ORIGINS=http://localhost:5173

AUTH_SESSION_TTL_HOURS=24
AUTH_SESSION_COOKIE_NAME=wisdomsystem_session
AUTH_COOKIE_SECURE=false
AUTH_COOKIE_SAMESITE=lax

AUTH_BOOTSTRAP_ADMIN_USERNAME=admin
AUTH_BOOTSTRAP_ADMIN_PASSWORD=Admin12345!
AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME=System Admin

AUTH_BOOTSTRAP_USER_USERNAME=demo_user
AUTH_BOOTSTRAP_USER_PASSWORD=User12345!
AUTH_BOOTSTRAP_USER_DISPLAY_NAME=Demo User
```

说明：

- 浏览器前端不再携带静态 `FASTAPI_API_KEY`
- Vue3 前端通过 `HttpOnly` Cookie 使用 `/api/v1/auth/*` 与 `/api/v1/me/*`
- DashScope 调用会自动为 `dashscope.aliyuncs.com` 与 `.aliyuncs.com` 追加 `NO_PROXY`，避免被本机代理错误接管
- 旧版 `X-API-Key` 接口仍保留，但已标记为 deprecated

## 启动方式

### 1. 启动 Redis（可选）

```bash
D:\Redis\redis-server.exe
```

### 2. 启动 FastAPI

```bash
conda activate wisdomsystem-py311
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

接口文档：

```text
http://localhost:8000/docs
```

### 3. 启动 Vue3 前端

```bash
cd web
npm run dev
```

页面地址：

```text
http://localhost:5173
```

### 4. 旧版 Streamlit 回退入口（可选）

```bash
conda activate wisdomsystem-py311
streamlit run app.py --server.port 8501
```

## 主要接口

### 浏览器鉴权

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### 用户自作用域接口

- `POST /api/v1/me/sessions`
- `GET /api/v1/me/sessions`
- `GET /api/v1/me/sessions/{session_id}`
- `POST /api/v1/me/chat/stream`
- `GET /api/v1/me/knowledge/chunks`
- `POST /api/v1/me/knowledge/documents/upload`
- `DELETE /api/v1/me/knowledge/chunks/{doc_id}`

### 管理员接口

- `GET /api/v1/admin/knowledge/chunks`
- `GET /api/v1/admin/knowledge/search`
- `POST /api/v1/admin/knowledge/documents/upload`
- `DELETE /api/v1/admin/knowledge/chunks/{doc_id}`
- `POST /api/v1/admin/knowledge/rebuild`

## 验证命令

```bash
conda activate wisdomsystem-py311
python -m compileall agent memory rag database utils model api services frontend app.py tests
python -m unittest tests.test_document_parsers -v
python -m unittest tests.test_rag_stability -v
python -m unittest tests.test_api_auth -v
python -m pip check
```

前端：

```bash
cd web
npm run build
npm run test
npx playwright test
```

## 维护约束

- Vue 前端只能通过 HTTP/SSE 调 FastAPI，不直接导入 Python 业务代码
- 私有知识改动必须保持严格用户隔离
- 删除 chunk 只删除向量库记录，不删除原始上传文件
- 重建索引前必须明确提示这是高风险操作
- 旧版 Streamlit 只做兼容回退，不再承载新增功能

- `version_notes/` 为本地长期复盘目录，默认不上传到 GitHub
更多维护说明见 `AGENTS.md`。
