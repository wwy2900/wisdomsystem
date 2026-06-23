"""Chat service used by FastAPI routes."""
from typing import Any, Generator

from agent.react_agent import ReactAgent
from agent.tools.runtime import get_source_references, reset_request_context, start_request_context
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
        for event_type, payload in self.chat_stream(user_id, session_id, message):
            if event_type == "answer_delta":
                answer_parts.append(str(payload.get("content", "")))
        return "".join(answer_parts)

    def chat_stream(self, user_id: str, session_id: str, message: str) -> Generator[tuple[str, dict[str, Any]], None, None]:
        session_data = self.session_manager.load_session(session_id)
        messages = list(session_data["messages"]) if session_data else []
        messages.append({"role": "user", "content": message})

        answer_parts: list[str] = []
        context_token = start_request_context(user_id=user_id, session_id=session_id)
        try:
            for chunk in self.agent.execute_stream(message, user_id=user_id, session_id=session_id):
                if chunk.startswith("[TOOL_RESULT") or chunk.startswith("[TOOL_THINK]"):
                    content = chunk[len("[TOOL_THINK]"):] if chunk.startswith("[TOOL_THINK]") else chunk
                    yield ("tool_event", {"content": content})
                elif chunk.startswith("[TOOL"):
                    yield ("tool_event", {"content": chunk})
                else:
                    answer_parts.append(chunk)
                    yield ("answer_delta", {"content": chunk})

            sources = get_source_references()
        finally:
            reset_request_context(context_token)

        assistant_response = "".join(answer_parts).strip()
        if assistant_response:
            assistant_message: dict[str, Any] = {"role": "assistant", "content": assistant_response}
            if sources:
                assistant_message["sources"] = sources
            messages.append(assistant_message)

        self.session_manager.save_session(session_id, messages, user_id=user_id)
        yield ("_done", {"sources": sources})
