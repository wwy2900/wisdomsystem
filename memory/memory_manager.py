from typing import Dict, Any, List, Optional
from .layers import ShortTermContext, UserProfileMemory, ConversationSummaryMemory, ExperienceMemory
from database.sqlite_db import SQLiteDatabase
from database.redis_cache import RedisCache


# 单例模式：避免重复初始化
_instance = None


class MemoryManager:
    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if self._initialized:
            return

        self.db = SQLiteDatabase()
        self.redis = RedisCache()
        
        try:
            from rag.rag_service import RagSummarizeService
            self.rag_service = RagSummarizeService()
        except Exception:
            self.rag_service = None

        self.l1 = ShortTermContext(self.redis)
        self.l2 = UserProfileMemory(self.db, self.redis)
        self.l3 = ConversationSummaryMemory(self.db, self.redis)
        self.l4 = ExperienceMemory(self.rag_service) if self.rag_service else None
        self._initialized = True

    def add_message(self, session_id: str, role: str, content: str):
        self.l1.add_message(session_id, role, content)

    def get_context(self, session_id: str) -> str:
        return self.l1.get_context(session_id)

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        return self.l2.get_or_create(user_id)

    def update_user_preference(self, user_id: str, key: str, value):
        self.l2.update_preference(user_id, key, value)

    def save_session_summary(self, user_id: str, session_id: str, messages: List[Dict[str, Any]]):
        self.l3.save_summary(user_id, session_id, messages)

    def get_user_summaries(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        return self.l3.get_user_summaries(user_id, limit)

    def add_success_case(self, user_id: str, title: str, content: str, metadata: Dict[str, Any] = {}):
        if self.l4:
            self.l4.add_success_case(user_id, title, content, metadata)

    def add_failure_case(self, user_id: str, title: str, content: str, metadata: Dict[str, Any] = {}):
        if self.l4:
            self.l4.add_failure_case(user_id, title, content, metadata)

    def query_experience(self, query: str) -> str:
        if self.l4:
            return self.l4.query_experience(query)
        return ""

    def build_full_context(self, user_id: str, session_id: str) -> str:
        parts = []

        profile = self.get_user_profile(user_id)
        if profile.get("name") or profile.get("preferences"):
            prefs = ", ".join([f"{k}: {v}" for k, v in profile.get("preferences", {}).items()])
            parts.append(f"用户信息: 姓名={profile.get('name', '未知')}, 偏好={prefs}")

        summaries = self.get_user_summaries(user_id, 3)
        if summaries:
            summary_texts = "\n".join([f"- {s['summary_text'][:50]}..." for s in summaries])
            parts.append(f"历史对话摘要:\n{summary_texts}")

        current_context = self.get_context(session_id)
        if current_context:
            parts.append(f"当前对话:\n{current_context}")

        return "\n\n".join(parts)
