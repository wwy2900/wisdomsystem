"""Chat service shared by FastAPI and the legacy Streamlit client."""
from typing import Generator

from agent.react_agent import ReactAgent
from database.redis_cache import RedisCache
from memory.session_manager import SessionManager
from utils.logger_handler import logger


class ChatService:
    """Coordinate session persistence and streaming agent execution."""

    def __init__(self):
        self.redis_cache = RedisCache()
        self.session_manager = SessionManager(self.redis_cache)
        self.agent = ReactAgent()
        logger.info("[ChatService] initialized")

    def create_session(self, user_id: str) -> str:
        return self.session_manager.create_session(user_id)

    def list_user_sessions(self, user_id: str) -> list[dict]:
        return self.session_manager.list_user_sessions(user_id)

    def get_session(self, session_id: str) -> dict | None:
        return self.session_manager.load_session(session_id)

    def get_user_session(self, session_id: str, user_id: str) -> dict | None:
        session = self.get_session(session_id)
        if not session or session.get("user_id") != user_id:
            return None
        return session

    def ensure_user_session(self, session_id: str | None, user_id: str) -> str:
        if session_id:
            existing_session = self.get_user_session(session_id, user_id)
            if existing_session:
                return session_id
        return self.create_session(user_id)

    def chat(self, user_id: str, session_id: str, message: str) -> str:
        answer_parts: list[str] = []
        for event_type, content in self.chat_stream(user_id, session_id, message):
            if event_type == "answer_delta":
                answer_parts.append(content)
        return "".join(answer_parts)

    def chat_stream(self, user_id: str, session_id: str, message: str) -> Generator[tuple[str, str], None, None]:
        session_data = self.session_manager.load_session(session_id)
        messages = session_data["messages"] if session_data else []
        messages.append({"role": "user", "content": message})

        answer_parts: list[str] = []
        for chunk in self.agent.execute_stream(message, user_id=user_id, session_id=session_id):
            if chunk.startswith("[TOOL_RESULT") or chunk.startswith("[TOOL_THINK]"):
                yield ("tool_event", chunk[len("[TOOL_THINK]"):] if chunk.startswith("[TOOL_THINK]") else chunk)
            elif chunk.startswith("[TOOL"):
                yield ("tool_event", chunk)
            else:
                answer_parts.append(chunk)
                yield ("answer_delta", chunk)

        assistant_response = "".join(answer_parts).strip()
        if assistant_response:
            messages.append({"role": "assistant", "content": assistant_response})

        self.session_manager.save_session(session_id, messages, user_id=user_id)
