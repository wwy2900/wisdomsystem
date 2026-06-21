"""聊天服务层：统一封装 ReactAgent + SessionManager + RedisCache"""
from typing import Generator
from agent.react_agent import ReactAgent
from database.redis_cache import RedisCache
from memory.session_manager import SessionManager
from utils.logger_handler import logger


class ChatService:
    """统一聊天服务，供 FastAPI 和 Streamlit 共用"""

    def __init__(self):
        self.redis_cache = RedisCache()
        self.session_manager = SessionManager(self.redis_cache)
        self.agent = ReactAgent()
        logger.info("[ChatService] 初始化完成")

    def create_session(self, user_id: str) -> str:
        """创建新会话，返回 session_id"""
        return self.session_manager.create_session(user_id)

    def list_user_sessions(self, user_id: str) -> list[dict]:
        """查询用户历史会话列表"""
        return self.session_manager.list_user_sessions(user_id)

    def get_session(self, session_id: str) -> dict | None:
        """查询单个会话详情"""
        return self.session_manager.load_session(session_id)

    def chat(self, user_id: str, session_id: str, message: str) -> str:
        """非流式聊天：等待完整回答后一次性返回"""
        answer_parts: list[str] = []
        for event_type, content in self.chat_stream(user_id, session_id, message):
            if event_type == "answer_delta":
                answer_parts.append(content)
        return "".join(answer_parts)

    def chat_stream(self, user_id: str, session_id: str, message: str) -> Generator[tuple[str, str], None, None]:
        """流式聊天：yield (event_type, content) 元组

        event_type:
            - "answer_delta": 最终回答片段（逐 token）
            - "tool_event": 工具调用/返回事件
        """
        # 加载现有会话消息
        session_data = self.session_manager.load_session(session_id)
        messages = session_data["messages"] if session_data else []

        # 添加用户消息
        messages.append({"role": "user", "content": message})

        # 执行流式查询
        answer_parts: list[str] = []
        for chunk in self.agent.execute_stream(message, user_id=user_id, session_id=session_id):
            if chunk.startswith("[TOOL_RESULT") or chunk.startswith("[TOOL_THINK]"):
                yield ("tool_event", chunk[len("[TOOL_THINK]"):] if chunk.startswith("[TOOL_THINK]") else chunk)
            elif chunk.startswith("[TOOL"):
                yield ("tool_event", chunk)
            else:
                answer_parts.append(chunk)
                yield ("answer_delta", chunk)

        # 保存 assistant 回答到会话
        assistant_response = "".join(answer_parts).strip()
        if assistant_response:
            messages.append({"role": "assistant", "content": assistant_response})

        # 保存会话
        self.session_manager.save_session(session_id, messages, user_id=user_id)
