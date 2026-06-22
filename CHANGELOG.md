# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

---

## [v1.7] - 2026-06-22

### Added

- 新增 `services/auth_service.py`，使用 `HttpOnly` Cookie 管理浏览器登录态
- 新增 SQLite `users` / `auth_sessions` 表
- 新增 Vue3 前端工程 `web/`
- 新增 Docker Compose 一键部署能力：`nginx(web) + fastapi(api) + redis`
- 新增部署文件：`docker-compose.yml`、`Dockerfile.api`、`web/Dockerfile`、`deploy/nginx.conf`、`.dockerignore`
- 新增浏览器接口：
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
  - `POST /api/v1/me/sessions`
  - `GET /api/v1/me/sessions`
  - `GET /api/v1/me/sessions/{session_id}`
  - `POST /api/v1/me/chat/stream`
  - `GET /api/v1/me/knowledge/chunks`
  - `POST /api/v1/me/knowledge/documents/upload`
  - `DELETE /api/v1/me/knowledge/chunks/{doc_id}`
- 新增管理员接口：
  - `GET /api/v1/admin/knowledge/chunks`
  - `GET /api/v1/admin/knowledge/search`
  - `POST /api/v1/admin/knowledge/documents/upload`
  - `DELETE /api/v1/admin/knowledge/chunks/{doc_id}`
  - `POST /api/v1/admin/knowledge/rebuild`
- 新增后端鉴权回归测试 `tests/test_api_auth.py`
- 新增前端单元测试与 Playwright 冒烟测试骨架

### Changed

- Docker Compose 的 Windows 部署说明补充为 `Docker Desktop + WSL2 backend` 主路径，并明确默认访问地址为 `http://localhost:8080`
- Docker Desktop 大体积数据目录说明统一收敛到 `D:\software\docker-desktop-data`
- FastAPI 增加 CORS，允许配置化的 Vue3 源站并开启带凭证请求
- 浏览器前端不再暴露 `FASTAPI_API_KEY`
- 聊天、会话、私有知识的浏览器访问统一改为从登录态解析当前用户
- 旧版 `/api/v1/*` API Key 路由标记为 deprecated
- 主文档改为以 `Docker Compose + Vue3 + FastAPI` 为默认运行方式
- `config/chroma.yml` 中 `md5_hex_store` 从根目录迁移到 `data/md5.txt`，与部署持久化目录对齐

### Fixed

- 修复 `Dockerfile.api` 在 Debian 依赖安装阶段对网络抖动更脆弱的问题，改为使用 HTTPS 源并增加重试
- 移除仓库内旧版 Streamlit 回退入口，避免运行路径和维护说明继续分叉
- 修复前端升级后静态 API Key 会暴露到浏览器的问题
- 修复普通用户可通过手工 `user_id` 切换访问其他用户会话/私有知识的风险
- 修复本机代理 `127.0.0.1:7890` 劫持 DashScope HTTPS 请求导致 `SSLEOFError` 的问题，现会自动为 `dashscope.aliyuncs.com` 追加 `NO_PROXY`
- 修复部署形态仍依赖手工分别启动前后端与 Redis 的问题，新增单域名反代和持久化挂载

## [v1.6] - 2026-06-22

### Added

- 新增 `rag/document_parsers/` 子模块与 `DocumentParserFactory`
- 新增 `txt/pdf/docx/xlsx/csv/md/json` 统一解析入口
- 新增结构化 metadata 字段：
  - `file_type`
  - `row_index`
  - `sheet_name`
  - `json_path`
  - `record_index`
  - `section_title`
  - `section_path`
  - `content_type`
  - `table_index`
  - `ocr_enabled`
  - `ocr_mode`
  - `ocr_bitmap_area_threshold`
- 新增 `tests/test_document_parsers.py`
- 新增 `tests/test_rag_stability.py`
- 新增 `DEPENDENCY_COMPATIBILITY.md`

### Changed

- `VectorStoreService` 改为通过 `DocumentParserFactory` 分派文档解析
- `BM25Retriever` 与向量入库共用同一套解析逻辑
- PDF 解析从 `PyPDFLoader` 纯文本抽取升级为 `Docling` 结构化解析
- PDF OCR 改为 `OcrAutoOptions` 自动兜底，仅依赖 Docling 的扫描页/位图区域判定
- `QuestionBasedSplitter` 对结构化 PDF 增加边界保护：
  - table 文档不再二次切分
  - text 文档优先透传，超长时仅在页内块中切分
- BM25 / RAG 在上传、删除、重建后自动失效并重载
- chunk `doc_id` 从顺序号改为稳定唯一 ID
- chunk 列表、过滤和删除链路改为底层分页查询和公开 API 路径
- MD5 记录从裸文本升级为结构化原子写入
- 混合检索去重从“前 100 字内容”升级为稳定文档身份键

### Fixed

- 修复 OCR Auto 模式下错误承诺“强制中英语言”的语义不一致问题
- 修复 BM25 语料在上传、删除、重建后长期陈旧的问题
- 修复删除后顺序 `doc_id` 复用和并发碰撞风险
- 修复知识库管理列表和统计依赖全量扫描导致的扩展性问题
- 修复 PDF 结构化 metadata 在后续 chunk 流程中丢失的风险

---

## [v1.5] - 2026-06-21

### Added

- 私有知识库按 `user_id` 隔离上传、检索、删除和列表查询
- 新增用户私有 chunk 查询接口：`GET /api/v1/knowledge/users/{user_id}/chunks`
- 聊天页固定上传栏前端桥接组件：`frontend/chat_upload_guard.py`
- 输入框左侧 `+` 上传入口与固定上传面板

### Changed

- `ReactAgent` 为每次请求构造用户作用域的 `rag_summarize` 工具
- `RagSummarizeService.rag_summarize()` 和 `retriever_docs()` 支持 `user_id`
- RAG 缓存 key 改为按用户范围隔离
- 会话 ID 改为高精度时间戳 + UUID 短后缀
- `SessionManager.list_user_sessions()` 增加 JSON 扫描兜底并重建 Redis 索引
- MD5 去重从“全局 md5”改为“scope + md5”
- Streamlit 聊天页上传栏开合状态改为纯前端临时状态，不再触发 rerun

### Fixed

- 修复不同用户间私有知识可能串查的问题
- 修复 Redis / SimpleCache 丢失后历史会话列表缺失的问题
- 修复不同用户上传同内容文件时被错误全局去重的问题
- 修复聊天页上传栏展开后无法收起、输入框失焦、点击侧边栏误收起的问题
- 修复上传栏开合触发右上角 `running` 的问题

---

## [v1.4] - 2026-06-21

### Changed

- Streamlit 改为纯前端客户端，通过 `frontend/api_client.py` 调用 FastAPI
- FastAPI 成为统一业务入口
- 聊天页面改为 SSE 流式输出

---

## [v1.3] - 2026-06-20

### Added

- FastAPI 后端入口与聊天、知识库路由
- `ChatService` 与 `KnowledgeService`
- Streamlit 知识库管理页
- 知识库上传、检索、删除 chunk、重建索引能力

### Changed

- RAG 召回、缓存和 BM25 检索性能优化

---

## [v1.2] - 2026-06-19

### Fixed

- 移除硬编码密钥
- 修复流式输出异常处理
- 用 `json.loads()` 替代危险的 `eval()`
- 修复 CSV 外部数据解析逻辑

---

## [v1.1] - 2026-06-19

### Changed

- 核心组件单例化
- 修复系统消息冲突
- 优化流式输出性能

---

## [v1.0] - 初始版本

### Added

- LangChain ReAct Agent
- 四层记忆体系
- RAG 检索链路
- Streamlit 前端
- Redis / 内存缓存降级
- 断点续聊与会话管理
