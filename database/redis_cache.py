import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional


class SimpleCache:
    def __init__(self):
        self.cache = {}
        self.expiry = {}

    def set(self, key: str, value: str):
        self.cache[key] = value
        self.expiry[key] = datetime.now() + timedelta(hours=2)

    def get(self, key: str) -> Optional[str]:
        if key not in self.cache:
            return None
        if datetime.now() > self.expiry[key]:
            del self.cache[key]
            del self.expiry[key]
            return None
        return self.cache[key]

    def expire(self, key: str, ttl: timedelta):
        if key in self.cache:
            self.expiry[key] = datetime.now() + ttl

    def lpush(self, key: str, value: str):
        if key not in self.cache:
            self.cache[key] = []
        self.cache[key].insert(0, value)
        self.expiry[key] = datetime.now() + timedelta(hours=2)

    def lrange(self, key: str, start: int, end: int) -> List[str]:
        if key not in self.cache:
            return []
        if datetime.now() > self.expiry[key]:
            del self.cache[key]
            del self.expiry[key]
            return []
        items = self.cache[key]
        if end == -1:
            end = len(items)
        return items[start:end]

    def ltrim(self, key: str, start: int, end: int):
        if key in self.cache:
            self.cache[key] = self.cache[key][start:end+1]


# 单例模式：避免重复初始化Redis连接
_instance = None


class RedisCache:
    def __new__(cls, host: str = "localhost", port: int = 6379, db: int = 0):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        if self._initialized:
            return
        
        try:
            import redis
            self.client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
            self.client.ping()
            self.use_redis = True
        except Exception:
            self.client = SimpleCache()
            self.use_redis = False
        self._initialized = True

    def set_conversation_context(self, session_id: str, messages: List[Dict[str, Any]], max_messages: int = 10):
        truncated = messages[-max_messages:]
        self.client.set(f"context:{session_id}", json.dumps(truncated))
        self.client.expire(f"context:{session_id}", timedelta(hours=2))

    def get_conversation_context(self, session_id: str) -> Optional[List[Dict[str, Any]]]:
        data = self.client.get(f"context:{session_id}")
        return json.loads(data) if data else None

    def cache_user_profile(self, user_id: str, profile: Dict[str, Any]):
        self.client.set(f"profile:{user_id}", json.dumps(profile))
        self.client.expire(f"profile:{user_id}", timedelta(hours=24))

    def get_cached_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        data = self.client.get(f"profile:{user_id}")
        return json.loads(data) if data else None

    def cache_summary(self, summary_id: str, summary: Dict[str, Any]):
        self.client.set(f"summary:{summary_id}", json.dumps(summary))
        self.client.expire(f"summary:{summary_id}", timedelta(hours=12))

    def set_session_user(self, session_id: str, user_id: str):
        self.client.set(f"session:{session_id}:user", user_id)
        self.client.expire(f"session:{session_id}:user", timedelta(hours=2))

    def get_session_user(self, session_id: str) -> Optional[str]:
        return self.client.get(f"session:{session_id}:user")

    def add_user_session(self, user_id: str, session_id: str):
        self.client.lpush(f"user:{user_id}:sessions", session_id)
        self.client.ltrim(f"user:{user_id}:sessions", 0, 9)

    def get_user_sessions(self, user_id: str) -> List[str]:
        return self.client.lrange(f"user:{user_id}:sessions", 0, -1) or []
