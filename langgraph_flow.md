# LangGraph 工作流程详解

## 一、核心流程图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              用户提问                                        │
│                    "给我生成我的使用报告"                                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LangGraph Agent                                   │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      create_react_agent()                             │  │
│  │                                                                      │  │
│  │   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐      │  │
│  │   │  Model   │───▶│  Think   │───▶│  Tool?   │───▶│  Action  │      │  │
│  │   │  (LLM)  │    │  思考     │    │  需要工具 │    │  执行工具 │      │  │
│  │   └──────────┘    └──────────┘    └──────────┘    └────┬─────┘      │  │
│  │        ▲                                      │         │            │  │
│  │        │                                      是        │            │  │
│  │        │                                      ▼         │            │  │
│  │        │                               ┌──────────┐    │            │  │
│  │        └───────────────────────────────│  Result  │◀───┘            │  │
│  │                                    │ 观察结果  │                  │  │
│  │                                    └──────────┘                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              返回回答                                        │
│              "好的，正在为您生成报告..."                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 二、ReAct 循环详解

ReAct = **Re**ason + **Act** (思考 + 行动)

### 循环步骤

```
                    ┌─────────────────────────────────────┐
                    │           开始循环                   │
                    └─────────────────┬───────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 步骤1: Think (思考)                                                        │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ LLM 分析当前状态：                                                       │ │
│ │ - 用户问题是什么？                                                       │ │
│ │ - 需要调用哪些工具？                                                     │ │
│ │ - 已经收集了哪些信息？                                                    │ │
│ │                                                                       │ │
│ │ 输出：决定是否调用工具，以及调用哪个工具                                    │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 步骤2: Act (行动)                                                          │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ 如果决定调用工具：                                                       │ │
│ │ → 调用对应的 @tool 装饰的函数                                            │ │
│ │                                                                       │ │
│ │ 如果决定不调用工具：                                                     │ │
│ │ → 跳到步骤4，生成最终回答                                                │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 步骤3: Observe (观察)                                                      │
│ ┌───────────────────────────────────────────────────────────────────────┐ │
│ │ 获取工具执行结果：                                                       │ │
│ │ - 天气查询结果                                                          │ │
│ │ - RAG检索结果                                                          │ │
│ │ - 用户信息结果                                                          │ │
│ │                                                                       │ │
│ │ 将结果添加到消息历史                                                     │ │
│ └───────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      ▼
                    ┌─────────────────────────────────────┐
                    │         循环继续？                   │
                    │   (回到步骤1，继续思考)               │
                    └─────────────────┬───────────────────┘
                                      │
                         ┌────────────┴────────────┐
                         ▼                         ▼
                        是                         否
                         │                         │
                         ▼                         ▼
                  ┌─────────────┐         ┌─────────────┐
                  │   继续循环   │         │  步骤4: 回答  │
                  └─────────────┘         └─────────────┘
```

---

## 三、代码映射

### 3.1 入口文件: [react_agent.py](file:///d:/1/LangChain-ReAct-Agent-main/agent/react_agent.py)

```python
# 1. 创建 Agent
self.agent = create_react_agent(
    model=chat_model,           # 通义千问模型
    tools=[...],                 # 可用工具列表
    messages_modifier=SystemMessage(content=system_prompt),  # 系统提示词
)

# 2. 接收用户输入
input_dict = {"messages": [{"role": "user", "content": query}]}

# 3. 启动 LangGraph 工作流 (流式输出)
for chunk in self.agent.stream(input_dict, stream_mode="values"):
    # chunk 包含每一步的状态变化
    yield latest_message.content
```

### 3.2 工具定义: [agent_tools.py](file:///d:/1/LangChain-ReAct-Agent-main/agent/tools/agent_tools.py)

```python
@tool                                    # ← LangGraph 识别的工具装饰器
def rag_summarize(query: str) -> str:    # ← RAG 检索工具
    """从向量存储中检索参考资料"""
    return rag.rag_summarize(query)

@tool
def get_weather(city: str) -> str:       # ← 天气查询工具
    """获取指定城市的天气"""
    return f"城市{city}天气为晴天..."

@tool
def get_user_location() -> str:          # ← 用户位置工具
    return random.choice(["深圳", "合肥", "杭州"])

@tool
def fetch_external_data(user_id: str, month: str) -> str:
    """从外部系统获取用户使用记录"""
    # 读取 CSV 文件，返回用户数据
```

### 3.3 中间件: [middleware.py](file:///d:/1/LangChain-ReAct-Agent-main/agent/tools/middleware.py)

```python
@wrap_tool_call                          # ← 工具执行前后的钩子
def monitor_tool(request, handler):
    logger.info(f"执行工具：{request.tool_call['name']}")
    result = handler(request)           # ← 真正执行工具
    logger.info(f"工具调用成功")

    # 如果是报告生成工具，设置上下文标记
    if request.tool_call['name'] == "fill_context_for_report":
        request.runtime.context["report"] = True

    return result

@before_model                            # ← 模型调用前的钩子
def log_before_model(state, runtime):
    logger.info(f"即将调用模型，带有{len(state['messages'])}条消息")

@dynamic_prompt                          # ← 动态切换提示词
def report_prompt_switch(request):
    # 根据上下文决定使用哪个提示词
    if request.runtime.context.get("report", False):
        return load_report_prompts()     # ← 报告生成场景的提示词
    return load_system_prompts()         # ← 普通场景的提示词
```

---

## 四、数据流向

### 4.1 工具调用流程

```
用户问题
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│                    LangGraph Agent                         │
│                                                            │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐             │
│  │  思考    │───▶│  决定    │───▶│  执行    │             │
│  │  工具    │    │  调用    │    │  工具    │             │
│  └──────────┘    └──────────┘    └──────────┘             │
│                                          │                 │
│                                          ▼                 │
│                                    ┌──────────┐             │
│                                    │  返回    │             │
│                                    │  结果    │             │
│                                    └──────────┘             │
└────────────────────────────────────────────────────────────┘
    │
    ▼
工具执行结果 (ToolMessage)
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│                    ChromaDB 向量库                          │
│  rag_summarize() → VectorStoreService → ChromaDB          │
│  从知识库中检索相关文档片段                                   │
└────────────────────────────────────────────────────────────┘
    │
    ▼
带上下文的回答
```

### 4.2 报告生成场景

```
用户: "给我生成我的使用报告"
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│                    LangGraph 循环                          │
│                                                            │
│  1. 调用 fill_context_for_report() 工具                   │
│     ↓                                                      │
│  2. 中间件 monitor_tool() 设置 runtime.context["report"]=True│
│     ↓                                                      │
│  3. 动态提示词切换 report_prompt_switch()                  │
│     ↓                                                      │
│  4. 调用 fetch_external_data(user_id, month) 获取数据      │
│     ↓                                                      │
│  5. 调用 get_user_location() 等获取更多信息                 │
│     ↓                                                      │
│  6. 生成报告                                               │
└────────────────────────────────────────────────────────────┘
```

---

## 五、RAG 检索流程

### 5.1 向量库初始化: [vector_store.py](file:///d:/1/LangChain-ReAct-Agent-main/rag/vector_store.py)

```python
self.vector_store = Chroma(
    collection_name="knowledge_base",
    embedding_function=embed_model,      # 文本嵌入模型
    persist_directory="./chroma_db",     # 持久化存储路径
)

# 文档分块
self.spliter = RecursiveCharacterTextSplitter(
    chunk_size=500,                       # 每块500字符
    chunk_overlap=50,                     # 重叠50字符
)
```

### 5.2 RAG 服务: [rag_service.py](file:///d:/1/LangChain-ReAct-Agent-main/rag/rag_service.py)

```python
def rag_summarize(query: str) -> str:
    # 1. 检索相关文档
    context_docs = self.retriever.invoke(query)

    # 2. 构建上下文
    context = ""
    for doc in context_docs:
        context += f"【参考资料】: {doc.page_content}\n"

    # 3. 调用 LLM 生成回答
    return self.chain.invoke({
        "input": query,      # 用户问题
        "context": context,  # 检索到的参考资料
    })
```

---

## 六、状态管理

### AgentState (LangGraph 内部状态)

```python
state = {
    "messages": [
        HumanMessage(content="给我生成我的使用报告"),
        AIMessage(content="让我先获取您的用户信息..."),
        ToolMessage(content="用户ID: 1001"),
        AIMessage(content="现在让我获取您的使用记录..."),
        ToolMessage(content={"特征": "...", "效率": "..."}),
        AIMessage(content="根据您的使用数据，我为您生成以下报告..."),
    ]
}
```

---

## 七、总结

| 组件 | 文件 | 作用 |
|------|------|------|
| **create_react_agent** | react_agent.py | LangGraph 核心，创建 ReAct Agent |
| **@tool 装饰器** | agent_tools.py | 定义可调用的工具函数 |
| **@wrap_tool_call** | middleware.py | 工具执行监控 |
| **@before_model** | middleware.py | 模型调用前拦截 |
| **@dynamic_prompt** | middleware.py | 动态切换提示词 |
| **ChromaDB** | vector_store.py | 向量存储 |
| **RAG Chain** | rag_service.py | 检索增强生成 |
| **ChatTongyi** | factory.py | 通义千问 LLM |

---

## 八、ReAct 伪代码

```python
def react_loop(user_question):
    messages = [HumanMessage(user_question)]

    while True:
        # 1. Think - LLM 决定是否需要工具
        response = llm.invoke(messages)

        if response.tool_calls:
            # 2. Act - 调用工具
            for tool_call in response.tool_calls:
                result = execute_tool(tool_call.name, tool_call.args)
                messages.append(ToolMessage(result))

            # 3. Observe - 将结果加入消息
            messages.append(response)
        else:
            # 4. Answer - 直接回答
            return response.content
```
