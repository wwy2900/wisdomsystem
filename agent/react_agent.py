from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessageChunk, ToolMessage
from langchain_core.tools import tool
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (
    fetch_external_data,
    fill_context_for_report,
    get_current_month,
    get_user_id,
    get_user_location,
    get_weather,
    rag_summarize,
    rag_summarize_for_user,
    reset_tool_user_id,
    set_tool_user_id,
)
from agent.tools.middleware import monitor_tool, log_before_model, report_prompt_switch
from utils.logger_handler import logger


# 单例模式：避免重复初始化
_instance = None


class ReactAgent:
    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if self._initialized:
            return

        self.system_prompt = load_system_prompts()
        self.agent = create_react_agent(
            model=chat_model,
            tools=[rag_summarize, get_weather, get_user_location, get_user_id,
                   get_current_month, fetch_external_data, fill_context_for_report],
        )
        
        self._setup_middleware(self.agent)
        
        from memory.memory_manager import MemoryManager
        self.memory_manager = MemoryManager()
        self._initialized = True

    def _setup_middleware(self, agent):
        """配置Agent中间件"""
        if hasattr(agent, 'middlewares'):
            agent.middlewares.append(monitor_tool)
            agent.middlewares.append(log_before_model)
            agent.middlewares.append(report_prompt_switch)
            logger.info("[ReactAgent] 中间件已配置")
        else:
            logger.warning("[ReactAgent] 当前LangGraph版本不支持middlewares属性，跳过中间件配置")

    def _build_agent_for_user(self, user_id: str):
        """Create a request-scoped agent so RAG tools cannot read another user's private chunks."""

        @tool("rag_summarize")
        def user_scoped_rag_summarize(query: str) -> str:
            """从向量存储中检索参考资料"""
            return rag_summarize_for_user(query, user_id=user_id)

        agent = create_react_agent(
            model=chat_model,
            tools=[
                user_scoped_rag_summarize,
                get_weather,
                get_user_location,
                get_user_id,
                get_current_month,
                fetch_external_data,
                fill_context_for_report,
            ],
        )
        self._setup_middleware(agent)
        return agent

    def execute_stream(self, query: str, user_id: str = "default", session_id: str = "default"):
        context = self.memory_manager.build_full_context(user_id, session_id)

        system_content = self.system_prompt
        if context:
            system_content += f"\n\n## 记忆上下文\n{context}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=query)
        ]

        self.memory_manager.add_message(session_id, "user", query)

        final_answer_parts: list[str] = []
        pending_tool_names: list[str] = []
        request_agent = self._build_agent_for_user(user_id)

        user_token = set_tool_user_id(user_id)
        try:
            for msg_chunk, _metadata in request_agent.stream({"messages": messages}, stream_mode="messages"):
                if isinstance(msg_chunk, AIMessageChunk):
                    content = msg_chunk.content
                    tool_call_chunks = getattr(msg_chunk, 'tool_call_chunks', None) or []

                    # 收集 tool_call_chunks 中的工具名称
                    for tc in tool_call_chunks:
                        name = getattr(tc, 'name', '') or ''
                        if name and (not pending_tool_names or pending_tool_names[-1] != name):
                            pending_tool_names.append(name)

                    # 如果有内容
                    if content:
                        content_str = content if isinstance(content, str) else str(content)
                        if pending_tool_names:
                            # 工具调用前的推理文本，包装后进思考过程栏
                            yield f"[TOOL_THINK]{content_str}"
                        else:
                            final_answer_parts.append(content_str)
                            yield content_str

                    # 当 tool_call_chunks 出现完整调用时输出标记
                    for tc in tool_call_chunks:
                        name = getattr(tc, 'name', '') or ''
                        args = getattr(tc, 'args', {}) or {}
                        args_str = ", ".join(f"{k}={v}" for k, v in args.items())
                        yield f"[TOOL:{name}:{args_str}]"

                elif isinstance(msg_chunk, ToolMessage):
                    tool_name = getattr(msg_chunk, 'name', 'unknown')
                    tool_content = getattr(msg_chunk, 'content', '')
                    preview = tool_content[:200] + "..." if len(tool_content) > 200 else tool_content
                    yield f"[TOOL_RESULT:{tool_name}:{preview}]"
                    # 工具返回后重置 pending
                    if pending_tool_names:
                        pending_tool_names = [n for n in pending_tool_names if n != tool_name]
        finally:
            reset_tool_user_id(user_token)

        final_answer = "".join(final_answer_parts).strip()
        if final_answer:
            self.memory_manager.add_message(session_id, "assistant", final_answer)


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)
