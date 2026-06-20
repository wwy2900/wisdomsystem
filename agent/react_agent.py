from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from model.factory import chat_model
from utils.prompt_loader import load_system_prompts
from agent.tools.agent_tools import (rag_summarize, get_weather, get_user_location, get_user_id,
                                     get_current_month, fetch_external_data, fill_context_for_report)
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
        
        self._setup_middleware()
        
        from memory.memory_manager import MemoryManager
        self.memory_manager = MemoryManager()
        self._initialized = True

    def _setup_middleware(self):
        """配置Agent中间件"""
        if hasattr(self.agent, 'middlewares'):
            self.agent.middlewares.append(monitor_tool)
            self.agent.middlewares.append(log_before_model)
            self.agent.middlewares.append(report_prompt_switch)
            logger.info("[ReactAgent] 中间件已配置")
        else:
            logger.warning("[ReactAgent] 当前LangGraph版本不支持middlewares属性，跳过中间件配置")

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

        final_answer = ""
        yielded_content = set()

        for chunk in self.agent.stream({"messages": messages}, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                if "messages" in node_output:
                    for msg in node_output["messages"]:
                        if isinstance(msg, AIMessage) and hasattr(msg, 'content'):
                            content = msg.content.strip()

                            if not content or content in yielded_content:
                                continue

                            # 判断是否为最终回答（无工具调用）
                            has_tool_calls = bool(getattr(msg, 'tool_calls', None))

                            if has_tool_calls:
                                # 工具调用前的思考，直接输出
                                yield content
                                yielded_content.add(content)
                            else:
                                # 最终回答，直接输出并记录
                                yield content
                                final_answer = content
                                yielded_content.add(content)

        if final_answer:
            self.memory_manager.add_message(session_id, "assistant", final_answer)


if __name__ == '__main__':
    agent = ReactAgent()

    for chunk in agent.execute_stream("给我生成我的使用报告"):
        print(chunk, end="", flush=True)