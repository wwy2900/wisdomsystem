# Changelog

## v1.3 (2026-06-20)

### 新增
- FastAPI 后端服务：SSE 流式聊天、会话管理、API Key 鉴权
- 知识库管理模块：上传文档、分页查看 chunk、检索预览、删除 chunk、重建索引
- Streamlit 知识库管理界面：侧边栏页面切换，4 个标签页（上传/检索/Chunk管理/重建）
- ChatService 和 KnowledgeService 统一服务层封装
- 并行向量+BM25 混合检索（ThreadPoolExecutor）
- 两级缓存：本地 dict 缓存 + Redis 缓存，TTL 86400s
- jieba 中文分词优化 BM25 检索，lru_cache 缓存分词结果
- Reranker 批量 embedding（适配 DashScope batch_size=10 限制）
- 语义检查器重试机制（指数退避，最多 3 次）
- 向量库管理方法：delete_document、clear_collection、_rebuild_md5_store
- 测试工具：check_doc_ids、rebuild_and_update、test_integration、update_cases

### 变更
- requirements.txt 新增 fastapi/uvicorn/sse-starlette/python-multipart
- .env 新增 FASTAPI_API_KEY
- 懒加载模式优化 RAG 组件初始化
- ContextualEnhancer 改为配置驱动（chroma.yml contextual_enhancer 开关）
- 流式输出增加工具调用标记（🔧/✅）

## v1.2 (2026-06-19)

### 新增
- 流式输出修复，中间件接入
- CSV 解析改进（csv.DictReader 替代字符串 split）

### 修复
- 安全修复：移除硬编码 API Key，eval 改 JSON 解析
- Agent 稳定性：工具返回值统一为字符串
- 依赖补齐

## v1.1 (2026-06-19)

### 新增
- 单例模式优化，避免重复初始化重型组件
- 系统消息冲突修复
- 性能优化：响应速度和内存占用改善

## v1.0 (初始版本)

### 新增
- 基础 Agent 框架：LangChain ReAct Agent + 流式对话
- 7 个工具：rag_summarize、get_weather、get_user_location、get_user_id、get_current_month、fetch_external_data、fill_context_for_report
- 四层记忆系统：L1 对话上下文、L2 用户画像、L3 近期摘要、L4 长期经验
- RAG 检索：向量检索、BM25、Query 改写、RRF 融合、Rerank 精排
- Streamlit 聊天界面：会话管理、断点续聊、思考过程展示
- Redis 缓存 + SQLite 数据库
- ChromaDB 向量库
