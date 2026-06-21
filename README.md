# WisdomSystem - 智扫通智能客服系统

基于 **LangChain + LangGraph + FastAPI + Streamlit** 构建的企业级智能客服项目，当前版本重点解决了统一前后端架构、私有知识库隔离、会话持久化和聊天页上传栏交互。

---

## 核心特性

### 1. 统一前后端架构

- Streamlit 仅作为前端客户端
- FastAPI 作为唯一业务入口
- 聊天通过 HTTP + SSE 调用后端
- 知识库管理、会话管理、流式问答都走同一套 API

### 2. 高级 RAG 检索

- Query 改写
- 语义校验
- 向量检索 + BM25 混合召回
- RRF 融合
- Rerank 精排
- 共享知识库与私有知识库联合检索

### 3. 私有知识库隔离

- 上传文件支持按 `user_id` 写入私有知识库
- RAG 只允许检索“共享知识 + 当前用户私有知识”
- 不会检索其他用户的私有 chunk
- 私有文件删除、chunk 列表和搜索都带用户边界

### 4. 会话持久化与断点续聊

- 会话保存到 `data/sessions/*.json`
- Redis 不可用时自动降级
- 历史会话列表支持从磁盘 JSON 兜底恢复
- 会话 ID 使用高精度时间戳 + UUID，避免快速创建冲突

### 5. 聊天页固定上传栏

- 上传入口为输入框左侧 `+`
- 上传面板固定在输入框上方
- 点击聊天区或输入框自动收起
- 点击侧边栏不影响上传栏
- 开合改为纯前端临时状态，不触发页面 `running`

---

## 当前版本重点更新

### v1.5

- 私有知识库按用户隔离检索
- RAG 缓存按用户范围隔离
- MD5 去重改为 `scope + md5`
- 会话列表支持 Redis 丢失后的磁盘 JSON 恢复
- 聊天页上传栏固定到底部，开合不再触发 Streamlit rerun

详细记录见 `CHANGELOG.md`。

---

## 项目结构

```text
WisdomSystem/
├─ agent/                  # ReAct Agent 与工具
├─ api/                    # FastAPI 入口与路由
├─ database/               # Redis / SQLite 封装
├─ frontend/               # Streamlit -> FastAPI 客户端与前端桥接
├─ memory/                 # 四层记忆与会话管理
├─ rag/                    # RAG 检索与向量库
├─ services/               # 聊天与知识库服务层
├─ data/                   # 知识库数据与上传目录
├─ tests/                  # 评估与测试脚本
├─ app.py                  # Streamlit 前端入口
├─ AGENTS.md               # Agent 维护说明
└─ CHANGELOG.md            # 版本更新记录
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

- `POST /api/v1/sessions`
- `GET /api/v1/users/{user_id}/sessions`
- `GET /api/v1/sessions/{session_id}`
- `POST /api/v1/chat`
- `POST /api/v1/chat/stream`

### 知识库

- `POST /api/v1/knowledge/documents/upload`
- `GET /api/v1/knowledge/chunks`
- `GET /api/v1/knowledge/search`
- `GET /api/v1/knowledge/users/{user_id}/chunks`
- `DELETE /api/v1/knowledge/chunks/{doc_id}`
- `POST /api/v1/knowledge/rebuild`

---

## 常用命令

语法检查：

```bash
conda activate wisdomsystem-py311
python -m compileall agent memory rag database utils model api services frontend app.py tests
```

RAG 评估：

```bash
conda activate wisdomsystem-py311
python tests/rag_evaluation.py
```

---

## 维护要点

- Streamlit 前端不要直接导入 Agent 或服务层
- 私有知识检索必须保持用户隔离
- 删除 chunk 不删除原始文件
- 重建索引前必须明确提示风险
- `.env`、数据库、向量库、上传文件、日志、本地调试产物不要提交

更多维护说明见 `AGENTS.md`。
