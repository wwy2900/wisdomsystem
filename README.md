# WisdomSystem

`WisdomSystem` 是一个面向智能客服场景的 RAG 系统，当前架构为：

- `FastAPI` 作为唯一业务后端
- `Vue 3 + Vite + TypeScript` 作为浏览器前端
- `LangChain + LangGraph` 负责 Agent 推理
- `ChromaDB + BM25 + Rerank` 负责检索
- `SQLite + Redis/SimpleCache + JSON` 负责认证、会话和缓存

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
web/                    新版 Vue3 前端
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

说明：

- 环境变量模板已收敛到根目录 `.env.example`
- 将 `.env.example` 复制为本地 `.env` 后，再替换其中的密钥和账号密码占位值
- Docker Compose 默认访问地址为 `http://localhost:8080`，模板中的 `FRONTEND_ORIGINS` 已同时覆盖 `8080` 与本地开发的 `5173`
- 浏览器前端不再携带静态 `FASTAPI_API_KEY`
- Vue3 前端通过 `HttpOnly` Cookie 使用 `/api/v1/auth/*` 与 `/api/v1/me/*`
- DashScope 调用会自动为 `dashscope.aliyuncs.com` 与 `.aliyuncs.com` 追加 `NO_PROXY`，避免被本机代理错误接管
- `.env.example` 不包含 `HTTP_PROXY` / `HTTPS_PROXY` / `NO_PROXY` 默认值，避免把本机网络策略写入模板
- 旧版 `X-API-Key` 接口仍保留，但已标记为 deprecated

## 一键部署

### 1. 安装并准备 Docker Desktop

Windows 推荐路径：

1. 安装 Docker Desktop for Windows，程序本体使用默认安装路径即可
2. 首次启动 Docker Desktop
3. 打开 Docker Desktop Settings，先把数据/磁盘镜像目录迁到 `D:\software\docker-desktop-data`
4. 确认 Docker Desktop 已正常启动，再继续下面的 Compose 步骤

说明：

- 这里要求落到 `D:\software` 的是 Docker 的大体积数据，不是强制 Docker Desktop 程序文件本体也安装到 D 盘
- 仓库内的 `docker-compose.yml` 不会硬编码宿主机 `D:\software` 路径；该路径只属于 Docker Desktop 本机设置

先验证本机 Docker CLI：

```bash
docker version
docker compose version
```

### 2. 准备配置

```bash
cp .env.example .env
```

Windows PowerShell 也可以使用：

```powershell
Copy-Item .env.example .env
```

至少需要修改：

- `DASHSCOPE_API_KEY`
- `AUTH_BOOTSTRAP_ADMIN_PASSWORD`
- `AUTH_BOOTSTRAP_USER_PASSWORD`

### 3. 启动 Compose

```bash
docker compose up -d --build
```

默认访问地址：

```text
http://localhost:8080
```

默认登录账户来自 `.env` 中的 `AUTH_BOOTSTRAP_*` 配置：

- 管理员：`AUTH_BOOTSTRAP_ADMIN_USERNAME`
- 普通用户：`AUTH_BOOTSTRAP_USER_USERNAME`

### 4. 持久化目录

Compose 会保留以下本地目录或卷：

- `data/`：SQLite、会话 JSON、私有知识上传文件、md5 去重记录
- `chroma_db/`：向量库
- `logs/`：运行日志
- `redis_data`：Redis 持久化卷

另外，Docker Desktop 自身的镜像/卷底层数据应通过 Docker Desktop 设置落到：

- `D:\software\docker-desktop-data`

### 5. 常用命令

```bash
docker compose ps
docker compose logs -f api
docker compose logs -f web
docker compose down
```

建议验证顺序：

1. `docker version`
2. `docker compose version`
3. `docker compose config`
4. `docker compose up -d --build`
5. 打开 `http://localhost:8080`

### 6. Windows Docker Desktop / WSL2 说明

- 当前仓库的 Docker Compose 主路径按 `Windows 10/11 + Docker Desktop + WSL2 backend` 设计
- Windows Home 只需要 Linux containers，不需要切换到 Windows containers
- 如果 Docker Desktop 一直停在启动中，先检查 BIOS/UEFI 是否已开启硬件虚拟化
- 如果 `wsl --update` 长时间卡住，可改为手工安装官方 WSL 更新包，再重新启动 Docker Desktop
- 本项目已按 `http://localhost:8080` 作为单入口验证通过，Vue3 静态资源与 `/api` 反代都走 Nginx

建议的 Windows 检查顺序：

```powershell
wsl --version
docker version
docker compose version
docker compose config
docker compose up -d --build
docker compose ps
```

关于 Docker 数据目录：

- Docker Desktop 程序本体可以保持默认安装路径
- 大体积镜像、卷与容器数据应迁到 `D:\software\docker-desktop-data`
- 仓库内的 `docker-compose.yml` 不会硬编码宿主机磁盘路径；`D:\software\docker-desktop-data` 只属于本机 Docker Desktop / WSL 数据落盘设置

首次部署后的浏览器验证：

1. 打开 `http://localhost:8080`
2. 使用 `.env` 中的 `AUTH_BOOTSTRAP_ADMIN_*` 或 `AUTH_BOOTSTRAP_USER_*` 登录
3. 普通用户进入 `/chat`
4. 管理员额外可进入 `/admin/knowledge`

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

接口文档：

```text
http://localhost:8000/docs
```

### 5. 启动 Vue3 前端

```bash
cd web
npm run dev
```

页面地址：

```text
http://localhost:5173
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
python -m compileall agent memory rag database utils model api services tests
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

- `version_notes/` 为本地长期复盘目录，默认不上传到 GitHub
更多维护说明见 `AGENTS.md`。
