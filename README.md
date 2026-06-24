# WisdomSystem

`WisdomSystem` 是一个面向智能客服场景的 RAG 系统，当前主架构为：
- `FastAPI` 作为唯一业务后端
- `Vue 3 + Vite + TypeScript` 作为浏览器前端
- `LangChain + LangGraph` 负责 Agent 推理与工具调用
- `ChromaDB + BM25 + Rerank` 负责知识检索
- `SQLite + Redis/SimpleCache + JSON` 负责认证、会话、客服数据与缓存

## 核心能力

- 聊天工作台：SSE 流式回答、工具过程展示、历史会话切换
- 用户注册与管理：登录页支持注册，管理员支持 `/admin/users` 创建和查看账号
- 私有知识隔离：当前登录用户只能访问自己的会话和私有知识
- 管理员知识库：共享知识上传、chunk 分页查看、检索预览、按 `doc_id` 删除、索引重建
- 客服业务工具：设备档案、耗材状态、售后政策、服务渠道 4 类只读工具
- 答案来源展示：assistant 消息支持折叠式 Sources 面板，展示知识库和业务工具来源
- 工具审计日志：工具调用会写入 SQLite 摘要审计日志，记录用户、会话、工具名、状态、耗时和摘要
- 多格式入库：`txt`、`pdf`、`docx`、`xlsx`、`csv`、`md`、`json`
- PDF 结构化解析：`Docling + OcrAutoOptions`

## 目录结构

```text
agent/                  ReAct Agent 与工具
api/                    FastAPI 路由、鉴权、SSE
config/                 项目配置
data/                   本地数据、客服结构化数据、会话与上传文件
database/               Redis / SQLite 封装
memory/                 会话与长期记忆
rag/                    解析器、检索、向量库
services/               聊天、知识库、认证、客服数据服务
web/                    Vue3 前端
tests/                  Python 回归测试
```

## 环境要求

- Docker Desktop / Docker Engine + Docker Compose
- 如需本地开发：Python 3.11、Node.js 18+
- DashScope API Key

## `.env` 配置

```bash
cp .env.example .env
```

至少需要修改：
- `DASHSCOPE_API_KEY`
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD`
- `AUTH_BOOTSTRAP_USER_PASSWORD`

说明：
- 环境变量模板统一放在根目录 `.env.example`
- 浏览器前端不再携带静态 `FASTAPI_API_KEY`
- Vue3 前端通过 `HttpOnly` Cookie 使用 `/api/v1/auth/*`、`/api/v1/me/*`、`/api/v1/admin/*`
- `FASTAPI_API_KEY` 仅作为兼容旧接口的 deprecated 配置保留
- DashScope 调用会对 `dashscope.aliyuncs.com` 与 `.aliyuncs.com` 自动补 `NO_PROXY`
- `.env.example` 不包含本机代理配置，避免把宿主机网络策略写入模板

## 一键部署

### 1. 安装 Docker Desktop

Windows 推荐路径：
1. 安装 Docker Desktop for Windows，程序本体使用默认安装路径即可
2. 首次启动后，将 Docker Desktop 数据目录迁到 `D:\software\docker-desktop-data`
3. 验证：

```bash
docker version
docker compose version
```

### 2. 准备配置

```bash
cp .env.example .env
```

PowerShell：

```powershell
Copy-Item .env.example .env
```

### 3. 启动 Compose

```bash
docker compose up -d --build
```

默认访问地址：

```text
http://localhost:8080
```

默认登录账号来自 `.env` 中的 `AUTH_BOOTSTRAP_*` 配置：
- 管理员：`AUTH_BOOTSTRAP_ADMIN_USERNAME`
- 普通用户：`AUTH_BOOTSTRAP_USER_USERNAME`

### 4. 持久化目录

Compose 会保留以下数据：
- `data/`：SQLite、会话 JSON、私有知识上传文件、客服结构化数据、md5 去重记录
- `chroma_db/`：向量库
- `logs/`：运行日志
- `redis_data`：Redis 持久化卷

## 本地开发启动

### 1. 后端安装

```bash
conda create -n wisdomsystem-py311 python=3.11
conda activate wisdomsystem-py311
pip install -r requirements.txt
```

### 2. 前端安装

```bash
cd web
npm install
```

### 3. 启动 Redis（可选）

```bash
D:\Redis\redis-server.exe
```

### 4. 启动 FastAPI

```bash
conda activate wisdomsystem-py311
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 启动 Vue3 前端

```bash
cd web
npm run dev
```

开发地址：
- FastAPI Docs: `http://localhost:8000/docs`
- Vue3: `http://localhost:5173`

## 主要页面

- `/login`：登录 / 注册
- `/chat`：聊天工作台、私有知识上传、来源展示
- `/admin/knowledge`：管理员知识库管理
- `/admin/users`：管理员用户管理
- `/403`：权限不足页

## 主要接口

### 浏览器鉴权
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/register`
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
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/users`
- `GET /api/v1/admin/knowledge/chunks`
- `GET /api/v1/admin/knowledge/search`
- `POST /api/v1/admin/knowledge/documents/upload`
- `DELETE /api/v1/admin/knowledge/chunks/{doc_id}`
- `POST /api/v1/admin/knowledge/rebuild`

### SSE 事件
- `answer_delta`
- `tool_event`
- `done`
- `error`

`done` 事件当前会返回 `session_id + sources`，前端据此展示引用来源。

## 验证命令

后端：

```bash
conda activate wisdomsystem-py311
python -m compileall agent memory rag database utils model api services tests
python -m unittest tests.test_document_parsers -v
python -m unittest tests.test_rag_stability -v
python -m unittest tests.test_api_auth -v
python -m unittest tests.test_customer_tools -v
python -m pip check
```

前端：

```bash
cd web
npm run build
npm run test
npx playwright test
```

## 当前版本

- 当前仓库主线版本：`v1.10`
- 版本重点：Bug 修复（新对话 404、异步流式响应）、BM25/RAG/ChatService 增强、量化评测框架、客服业务工具、Docker Compose 主部署路径
