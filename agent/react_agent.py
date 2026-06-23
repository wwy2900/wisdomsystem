from langchain_core.messages import AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langgraph.prebuilt import create_react_agent

from agent.tools.agent_tools import (
    lookup_device_consumables,
    lookup_service_channels,
    lookup_service_policy,
    lookup_user_devices,
    rag_summarize,
)
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts


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
            tools=[
                rag_summarize,
                lookup_user_devices,
                lookup_device_consumables,
                lookup_service_policy,
                lookup_service_channels,
            ],
        )

        from memory.memory_manager import MemoryManager

        self.memory_manager = MemoryManager()
        self._initialized = True

    def execute_stream(self, query: str, user_id: str = "default", session_id: str = "default"):
        context = self.memory_manager.build_full_context(user_id, session_id)

        system_content = self.system_prompt
        if context:
            system_content += f"\n\n## Memory Context\n{context}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=query),
        ]

        self.memory_manager.add_message(session_id, "user", query)

        final_answer_parts: list[str] = []
        pending_tool_names: list[str] = []

        for msg_chunk, _metadata in self.agent.stream({"messages": messages}, stream_mode="messages"):
            if isinstance(msg_chunk, AIMessageChunk):
                content = msg_chunk.content
                tool_call_chunks = getattr(msg_chunk, "tool_call_chunks", None) or []

                for tool_call in tool_call_chunks:
                    name = getattr(tool_call, "name", "") or ""
                    if name and (not pending_tool_names or pending_tool_names[-1] != name):
                        pending_tool_names.append(name)

                if content:
                    content_str = content if isinstance(content, str) else str(content)
                    if pending_tool_names:
                        yield f"[TOOL_THINK]{content_str}"
                    else:
                        final_answer_parts.append(content_str)
                        yield content_str

                for tool_call in tool_call_chunks:
                    name = getattr(tool_call, "name", "") or ""
                    args = getattr(tool_call, "args", {}) or {}
                    args_str = ", ".join(f"{key}={value}" for key, value in args.items())
                    yield f"[TOOL:{name}:{args_str}]"

            elif isinstance(msg_chunk, ToolMessage):
                tool_name = getattr(msg_chunk, "name", "unknown")
                tool_content = getattr(msg_chunk, "content", "")
                preview = tool_content[:200] + "..." if len(tool_content) > 200 else tool_content
                yield f"[TOOL_RESULT:{tool_name}:{preview}]"
                if pending_tool_names:
                    pending_tool_names = [name for name in pending_tool_names if name != tool_name]

        final_answer = "".join(final_answer_parts).strip()
        if final_answer:
            self.memory_manager.add_message(session_id, "assistant", final_answer)
