import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from database.redis_cache import RedisCache


# 单例模式：避免重复初始化
_instance = None


class SessionManager:
    def __new__(cls, redis: RedisCache = None, storage_dir: str = "data/sessions"):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self, redis: RedisCache = None, storage_dir: str = "data/sessions"):
        if self._initialized:
            return
        
        if redis is None:
            redis = RedisCache()
        self.redis = redis
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self._initialized = True

    def create_session(self, user_id: str) -> str:
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.redis.set_session_user(session_id, user_id)
        self.redis.add_user_session(user_id, session_id)
        return session_id

    def save_session(self, session_id: str, messages: List[Dict[str, Any]]):
        session_data = {
            "session_id": session_id,
            "user_id": self.redis.get_session_user(session_id) or "unknown",
            "messages": messages,
            "saved_at": datetime.now().isoformat()
        }

        file_path = os.path.join(self.storage_dir, f"{session_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)

    def load_session(self, session_id: str) -> Optional[dict]:
        file_path = os.path.join(self.storage_dir, f"{session_id}.json")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def list_user_sessions(self, user_id: str) -> List[dict]:
        session_ids = self.redis.get_user_sessions(user_id)

        sessions = []
        for session_id in session_ids:
            file_path = os.path.join(self.storage_dir, f"{session_id}.json")
            if os.path.exists(file_path):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_msg = data["messages"][-1]["content"][:30] if data["messages"] else "空会话"
                    sessions.append({
                        "session_id": session_id,
                        "preview": last_msg,
                        "saved_at": data.get("saved_at", "")
                    })

        return sessions
