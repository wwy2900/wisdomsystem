# Agent 系统关键说明

本文档记录“智扫通·智能客服”项目当前版本的核心维护信息，重点覆盖 Agent、FastAPI、Vue3 前端、浏览器鉴权、RAG、会话持久化、私有知识隔离、多格式文档解析、PDF OCR，以及知识库管理链路。详细背景和使用说明见 `README.md`、`CHANGELOG.md`。

---

## 1. 系统架构

项目当前为 `Vue3 + FastAPI` 主架构，旧版 `Streamlit` 仅作为兼容回退入口保留。

| 层级 | 说明 | 关键文件 |
| --- | --- | --- |
| 用户界面层 | Vue3 前端，负责登录页、聊天页、管理员知识库页 | `web/src/pages/`, `web/src/router/`, `web/src/stores/` |
| API 服务层 | FastAPI 后端、Cookie 鉴权、角色权限、SSE 流式输出 | `api/main.py`, `api/routes/`, `api/dependencies.py` |
| 服务层 | 聊天、知识库、认证等业务封装 | `services/chat_service.py`, `services/knowledge_service.py`, `services/auth_service.py` |
| Agent 层 | ReAct Agent 推理、工具调用、用户级上下文注入 | `agent/react_agent.py`, `agent/tools/agent_tools.py` |
| 记忆层 | 会话上下文、用户画像、会话摘要、长期经验 | `memory/` |
| RAG 层 | 文档解析、向量检索、BM25、Rerank、私有知识隔离 | `rag/` |
| 存储层 | Redis/SimpleCache、SQLite、ChromaDB、JSON 会话文件 | `database/`, `data/sessions/`, `chroma_db/` |
| 兼容前端层 | 旧版 Streamlit 客户端，仅供回退验证 | `app.py`, `frontend/` |

---

## 2. 当前关键能力

### Vue3 主前端

- 主前端目录为 `web/`
- 当前页面与路由：
  - `/login`
  - `/chat`
  - `/admin/knowledge`
  - `/403`
- 前端状态拆分为：
  - `authStore`
  - `sessionStore`
  - `chatStore`
  - `knowledgeStore`
- 浏览器前端只能通过 HTTP/SSE 调 FastAPI，不直接导入 Python 业务代码

### 浏览器鉴权与角色权限

- 浏览器侧鉴权已从静态 `FASTAPI_API_KEY` 改为 `HttpOnly Cookie`
- `AuthService` 使用 SQLite 的 `users` / `auth_sessions` 表管理登录态
- 当前角色固定为：
  - `user`
  - `admin`
- 普通用户只能访问：
  - 自己的会话
  - 自己的私有知识
  - 共享知识参与的检索结果
- 管理员额外可访问：
  - 共享知识上传
  - chunk 全局查看
  - chunk 删除
  - 索引重建
- 浏览器普通业务场景下不再由前端显式传 `user_id`

### 私有知识库隔离

- `rag_summarize` 已按 `user_id` 注入用户范围
- RAG 检索范围为“共享知识库 + 当前用户私有知识”
- 不会命中其他用户私有 chunk
- RAG 缓存 key 已带用户范围
- 私有 chunk 的上传、检索、删除、列表查询都带 `user_id` 边界

### 会话持久化

- `session_id` 使用时间戳 + UUID 短后缀生成
- 会话写入 `data/sessions/*.json`
- `list_user_sessions(user_id)` 在 Redis 索引丢失时会扫描磁盘 JSON 兜底，并重建 Redis 映射

### 多格式文档解析

- 已接入 `DocumentParserFactory`
- 当前支持：`txt`, `pdf`, `docx`, `xlsx`, `csv`, `md`, `json`
- `csv/xlsx/json/md/docx` 先结构化拆分为多个 `Document`，再进入现有 chunk 流程
- `txt/pdf` 已统一迁入工厂体系

### PDF 结构化解析与 OCR

- `PdfParser` 使用 `Docling`
- 输出为“页内 section 文本块 + 独立 table 文档”
- metadata 保留：
  - `file_type`
  - `page`
  - `section_path`
  - `section_title`
  - `content_type`
  - `table_index`
  - `ocr_enabled`
  - `ocr_mode`
  - `ocr_bitmap_area_threshold`
- OCR 使用 `OcrAutoOptions`
- 只依赖 Docling 的自动位图判定做扫描页兜底
- 当前不承诺强制 OCR 语言控制

### 知识库管理稳定性

- chunk `doc_id` 已从顺序号改为稳定唯一 ID
- MD5 记录已从裸文本升级为结构化原子写入
- 上传、删除、重建后会失效 RAG/BM25 缓存
- chunk 列表与过滤改为底层分页查询，不再每次全量扫描后分页
- 删除链路优先使用 Chroma 公开 API，不再在业务层散落 `_collection` 直接访问

---

## 3. FastAPI 接口

FastAPI 入口：`api/main.py`

启动命令：

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

接口文档：

```text
http://localhost:8000/docs
```

### 浏览器鉴权

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | 用户名/密码登录并签发 Cookie |
| POST | `/api/v1/auth/logout` | 清理登录态 |
| GET | `/api/v1/auth/me` | 恢复当前登录用户 |

### 用户自作用域接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| POST | `/api/v1/me/sessions` | 为当前登录用户创建会话 |
| GET | `/api/v1/me/sessions` | 查询当前登录用户历史会话 |
| GET | `/api/v1/me/sessions/{session_id}` | 查询当前登录用户会话详情 |
| POST | `/api/v1/me/chat/stream` | SSE 流式聊天 |
| GET | `/api/v1/me/knowledge/chunks` | 查询当前登录用户私有 chunk |
| POST | `/api/v1/me/knowledge/documents/upload` | 上传私有知识文档并立即入库 |
| DELETE | `/api/v1/me/knowledge/chunks/{doc_id}` | 删除当前登录用户私有 chunk |

### 管理员接口

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/api/v1/admin/knowledge/chunks` | 分页查看 chunk，可按 `user_id` 过滤 |
| GET | `/api/v1/admin/knowledge/search` | 检索预览，可按 `user_id` 过滤 |
| POST | `/api/v1/admin/knowledge/documents/upload` | 上传共享知识文档并立即入库 |
| DELETE | `/api/v1/admin/knowledge/chunks/{doc_id}` | 删除指定 chunk |
| POST | `/api/v1/admin/knowledge/rebuild` | 清空并重建索引 |

### 兼容保留的旧接口

- 旧版 `X-API-Key` 接口仍保留在 `/api/v1/*` 与 `/api/v1/knowledge/*`
- 这些接口当前为兼容层，已标记 deprecated
- Vue3 前端不得继续使用这些旧接口

---

## 4. 维护约束

- 主前端为 Vue3，新增前端能力优先落在 `web/`
- 旧版 `Streamlit` 只做兼容回退，不再承载新增功能
- Vue 前端只能通过 `web/src/api/*` 调 FastAPI
- 不要在前端直接导入 Agent、SessionManager、VectorStore 或服务层
- 私有知识相关改动必须保持严格用户隔离
- 删除 chunk 只删除向量库记录，不删除原始上传文件
- 重建索引会清空当前向量库，执行前必须明确提示
- 不要把 OCR Auto fallback 表述成“强制中英语言 OCR”
- `doc_id` 相关逻辑不能再依赖递增顺序号
- 修改 RAG、知识库边界或解析链路时，优先补测试而不是只改实现
- 修改浏览器鉴权、角色权限或 `me/admin` 路由边界时，必须补接口测试
- 每次版本升级后，必须在根目录 `version_notes/` 下新增一份版本复盘文档
- 版本复盘文档命名统一为 `v{新版本}_from_v{上一版本}.md`
- 版本复盘文档至少记录本版本期间的关键问题、解决思路和落地方法
- `.env`、数据库、向量库、上传文件、日志和本地浏览器验证产物不得提交

若修改 RAG、会话或知识库边界逻辑，至少运行一次：

```bash
python -m compileall agent memory rag database utils model api services frontend app.py tests
```

推荐同时运行：

```bash
python -m unittest tests.test_document_parsers -v
python -m unittest tests.test_rag_stability -v
python -m unittest tests.test_api_auth -v
python -m pip check
```

前端改动推荐同时运行：

```bash
cd web
npm run build
npm run test
npx playwright test
```

---

## 5. 启动与验证

默认 Conda 环境：`wisdomsystem-py311`

### 启动顺序

1. Redis（可选）

```bash
D:\Redis\redis-server.exe
```

2. FastAPI

```bash
conda activate wisdomsystem-py311
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

3. Vue3 前端

```bash
cd web
npm install
npm run dev
```

页面地址：

```text
FastAPI Docs: http://localhost:8000/docs
Vue3:         http://localhost:5173
```

4. Streamlit 回退入口（可选）

```bash
conda activate wisdomsystem-py311
streamlit run app.py --server.port 8501
```

### 常用检查

语法检查：

```bash
conda activate wisdomsystem-py311
python -m compileall agent memory rag database utils model api services frontend app.py tests
```

解析器、稳定性与鉴权测试：

```bash
conda activate wisdomsystem-py311
python -m unittest tests.test_document_parsers -v
python -m unittest tests.test_rag_stability -v
python -m unittest tests.test_api_auth -v
```

依赖检查：

```bash
conda activate wisdomsystem-py311
python -m pip check
```

前端验证：

```bash
cd web
npm run build
npm run test
npx playwright test
```

RAG 评估：

```bash
conda activate wisdomsystem-py311
python tests/rag_evaluation.py
```

---

## 6. 版本记录

| 版本 | 日期 | 说明 |
| --- | --- | --- |
| v1.7 | 2026-06-22 | Vue3 前端迁移、Cookie 鉴权、`me/admin` 路由、浏览器角色权限模型 |
| v1.6 | 2026-06-22 | 多格式解析工厂、Docling PDF/OCR、BM25 刷新、稳定 doc_id、知识库管理链路重构 |
| v1.5 | 2026-06-21 | 私有知识隔离、会话 JSON 兜底、作用域 MD5 去重、聊天上传栏前端化 |
| v1.4 | 2026-06-21 | Streamlit 改为 FastAPI 客户端，统一前后端架构 |
| v1.3 | 2026-06-20 | FastAPI 服务层和知识库管理模块 |
| v1.2 | 2026-06-19 | 安全修复、流式输出修复、CSV 解析、依赖补齐 |
| v1.1 | 2026-06-19 | 单例优化、系统消息冲突修复、性能优化 |
| v1.0 | 初始版本 | 基础 Agent、对话和工具系统 |

**适用版本：** v1.7  
**最后更新：** 2026-06-22
