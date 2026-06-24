# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

---

## [v1.10] - 2026-06-24

### Fixed

- 修复 `SessionManager.create_session` 不创建会话文件导致新对话 404 的问题
- 修复 `chat_stream` 异步处理逻辑，确保 SSE 流式响应正确返回
- 修复 `onclose` 回调重复报错问题（添加 `terminatedByError` 标志）
- 登录/注册页面改进错误信息展示（`describeRequestError`）

### Added

- 新增 `AuthService.warmup_async` 方法，启动时异步预热 ChatService
- 新增 `utils/dashscope_runtime.py`（DashScope 运行时工具）
- 新增 `utils/model_cache.py`（模型缓存工具）

### Changed

- `api/routes/auth.py` 路由函数从同步改为异步
- `api/routes/me.py` chat_stream 使用 `asyncio.Queue` + `threading.Thread` 重构
- `rag/bm25_retriever.py` BM25 检索器增强（82 行修改）
- `services/chat_service.py` ChatService 增强（15 行修改）
- `rag/rag_service.py` RAG 服务增强（5 行修改）
- `tests/test_rag_stability.py` 新增测试用例（25 行）

---

## [v1.9] - 2026-06-23

### Added

- 新增量化评测框架（`eval/` 目录），覆盖 RAG 检索、RAG 生成、Agent 工具选择、SSE 流式性能四类评测
- 新增评测数据集：
  - `eval/rag_cases.jsonl`（50 条，启发式预填 `expected_doc_ids`）
  - `eval/agent_cases.jsonl`（15 条，覆盖 5 类工具）
  - `eval/no_answer_cases.jsonl`（5 条，无答案场景）
- 新增评测脚本：
  - `eval/evaluate_retrieval.py`（Recall@K / MRR，支持 vector_only / bm25_only / hybrid_rerank 三种模式）
  - `eval/evaluate_answer.py`（Keyword Coverage / Citation Rate / Answer Pass Rate / No-answer Accuracy）
  - `eval/evaluate_agent.py`（Tool Selection Accuracy / First Tool Accuracy / Tool Success Rate / Source Rate）
  - `eval/benchmark_stream.py`（TTFT / Total Latency / P50 / P95，支持 service 和 http 两种模式）
- 新增评测工具：`eval/eval_utils.py`、`eval/migrate_test_cases.py`、`eval/export_chunks.py`、`eval/generate_markdown_report.py`
- 新增量化评测报告 `docs/evaluation_report.md`
- 新增版本复盘文档 `version_notes/v1.9_from_v1.8.md`

### Changed

- `.gitignore` 新增 `docs/evaluation_report.md` 和 `eval/README.md` 白名单
- `.gitignore` 新增 `eval/reports/*.json` 忽略规则（保留 `.gitkeep`）
- `AGENTS.md`、`README.md` 版本号同步更新到 v1.9

---

## [v1.8] - 2026-06-23

### Added

- 新增公开注册接口 `POST /api/v1/auth/register`
- 新增管理员用户管理接口：
  - `GET /api/v1/admin/users`
  - `POST /api/v1/admin/users`
- 新增管理员用户管理页面 `/admin/users`
- 新增 4 类只读客服业务工具：
  - `lookup_user_devices`
  - `lookup_device_consumables`
  - `lookup_service_policy`
  - `lookup_service_channels`
- 新增客服结构化数据目录 `data/customer_support/`
- 新增 SQLite 客服与审计表：
  - `customer_devices`
  - `device_consumables`
  - `tool_audit_logs`
- 新增聊天答案来源模型与前端 Sources 折叠面板
- 新增工具审计运行时上下文与客服工具测试 `tests/test_customer_tools.py`

### Changed

- 清理旧 demo/report 工具链，移除天气、位置、硬编码用户 ID、外部 CSV 报告工具及相关提示词分支
- Agent 工具集调整为“知识检索 + 客服业务工具”真实能力集合
- `POST /api/v1/me/chat/stream` 与兼容流式接口的 `done` 事件负载增加 `sources`
- 会话消息结构扩展为 `role + content + optional sources`，历史会话可回看来源
- 聊天页 assistant 消息支持折叠式引用来源展示
- README、AGENTS、CHANGELOG 更新为当前 Vue3 + FastAPI + 客服工具版本说明

### Fixed

- 修复聊天回答无法向用户展示知识库/业务工具来源的问题
- 修复工具调用缺少持久化审计留痕的问题
- 修复客服工具仍混入 demo 样例逻辑、与真实业务场景不一致的问题

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
- 新增管理员知识库接口：
  - `GET /api/v1/admin/knowledge/chunks`
  - `GET /api/v1/admin/knowledge/search`
  - `POST /api/v1/admin/knowledge/documents/upload`
  - `DELETE /api/v1/admin/knowledge/chunks/{doc_id}`
  - `POST /api/v1/admin/knowledge/rebuild`
- 新增后端鉴权回归测试 `tests/test_api_auth.py`
- 新增前端单元测试与 Playwright 冒烟测试骨架

### Changed

- FastAPI 增加 CORS，允许配置化 Vue3 源站并开启带凭证请求
- 浏览器前端不再暴露 `FASTAPI_API_KEY`
- 聊天、会话、私有知识的浏览器访问统一改为从登录态解析当前用户
- 旧版 `/api/v1/*` API Key 路由标记为 deprecated
- 主文档改为以 `Docker Compose + Vue3 + FastAPI` 作为默认运行方式
- `config/chroma.yml` 中 `md5_hex_store` 从根目录迁移到 `data/md5.txt`

### Fixed

- 移除仓库内旧版 Streamlit 回退入口，避免运行路径继续分叉
- 修复前端升级后静态 API Key 暴露到浏览器的问题
- 修复普通用户可通过手工 `user_id` 切换访问他人会话或私有知识的风险
- 修复本机代理错误接管 DashScope HTTPS 请求导致 `SSLEOFError` 的问题

---

## [v1.6] - 2026-06-22

### Added

- 新增 `rag/document_parsers/` 子模块与 `DocumentParserFactory`
- 新增 `txt/pdf/docx/xlsx/csv/md/json` 统一解析入口
- 新增 `tests/test_document_parsers.py`
- 新增 `tests/test_rag_stability.py`
- 新增 `DEPENDENCY_COMPATIBILITY.md`

### Changed

- PDF 解析升级为 `Docling` 结构化解析 + OCR Auto fallback
- BM25 与向量入库统一共享同一套解析逻辑
- chunk `doc_id` 改为稳定唯一 ID
- chunk 列表、过滤和删除链路改为底层分页查询与公开 API
- MD5 记录从裸文本升级为结构化原子写入

### Fixed

- 修复 BM25 语料、删除后 `doc_id` 重用、PDF metadata 丢失等稳定性问题

---

## [v1.5] - 2026-06-21

### Added

- 私有知识库按 `user_id` 隔离上传、检索、删除和列表查询
- 新增用户私有 chunk 查询接口 `GET /api/v1/knowledge/users/{user_id}/chunks`

### Changed

- `ReactAgent` 为每次请求构造用户作用域的 `rag_summarize`
- `RagSummarizeService` 支持按 `user_id` 作用域检索
- RAG 缓存 key 改为按用户范围隔离
- 会话 ID 改为时间戳 + UUID 短后缀

### Fixed

- 修复私有知识串查、Redis 会话索引丢失、作用域 MD5 去重错误等问题
