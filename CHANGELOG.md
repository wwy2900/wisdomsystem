# Changelog

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，版本号遵循语义化版本。

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
