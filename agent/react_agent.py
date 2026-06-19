from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                     get_current_month, fetch_external_data, fill_context_for_report)


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
        from memory.memory_manager import MemoryManager
        self.memory_manager = MemoryManager()
        self._initialized = True

    def execute_stream(self, query: str, user_id: str = "default", session_id: str = "default"):
        context = self.memory_manager.build_full_context(user_id, session_id)

        # 构建消息列表，包含系统消息（带上下文）和用户消息
        system_content = self.system_prompt
        if context:
            system_content += f"\n\n## 记忆上下文\n{context}"

        messages = [
            SystemMessage(content=system_content),
            HumanMessage(content=query)
        ]

        self.memory_manager.add_message(session_id, "user", query)

        for chunk in self.agent.stream({"messages": messages}, stream_mode="values"):
            latest_message = chunk["messages"][-1]
            if hasattr(latest_message, 'content') and latest_message.content:
                content = latest_message.content.strip()
                self.memory_manager.add_message(session_id, "assistant", content)
                yield content + "\n"


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)