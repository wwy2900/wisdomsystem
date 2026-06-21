import json
import os
import socket
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from utils.logger_handler import logger


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
            self.cache[key] = self.cache[key][start:end + 1]

    def lrem(self, key: str, count: int, value: str):
        if key not in self.cache:
            return 0
        removed = 0
        remaining = []
        for item in self.cache[key]:
            if item == value and (count == 0 or removed < abs(count)):
                removed += 1
                continue
            remaining.append(item)
        self.cache[key] = remaining
        return removed


_instance = None


def _get_bool_env(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def _get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning("Invalid %s=%r, using default %s", name, value, default)
        return default


def _get_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        logger.warning("Invalid %s=%r, using default %s", name, value, default)
        return default


def _is_tcp_reachable(host: str, port: int, timeout: float) -> bool:
    try:
        addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        logger.warning("Redis address lookup failed for %s:%s: %s", host, port, exc)
        return False

    if not addresses:
        return False

    deadline = time.monotonic() + timeout
    per_attempt_timeout = max(min(timeout / len(addresses), timeout), 0.1)

    for family, socktype, proto, _, address in addresses:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return False

        sock = socket.socket(family, socktype, proto)
        try:
            sock.settimeout(min(per_attempt_timeout, remaining))
            sock.connect(address)
            return True
        except OSError:
            continue
        finally:
            sock.close()

    return False


class RedisCache:
    def __new__(cls, host: str | None = None, port: int | None = None, db: int | None = None):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self, host: str | None = None, port: int | None = None, db: int | None = None):
        if self._initialized:
            return

        self.backend = "simple_cache"
        self.use_redis = False

        if not _get_bool_env("REDIS_ENABLED", True):
            self.client = SimpleCache()
            logger.info("Redis disabled by REDIS_ENABLED=false, using SimpleCache")
            self._initialized = True
            return

        redis_host = host or os.getenv("REDIS_HOST", "localhost")
        redis_port = port if port is not None else _get_int_env("REDIS_PORT", 6379)
        redis_db = db if db is not None else _get_int_env("REDIS_DB", 0)
        connect_timeout = _get_float_env("REDIS_CONNECT_TIMEOUT", 1.0)
        socket_timeout = _get_float_env("REDIS_SOCKET_TIMEOUT", 1.0)

        if not _is_tcp_reachable(redis_host, redis_port, connect_timeout):
            self.client = SimpleCache()
            logger.warning(
                "Redis unreachable at %s:%s/%s within %.1fs, using SimpleCache",
                redis_host,
                redis_port,
                redis_db,
                connect_timeout,
            )
            self._initialized = True
            return

        try:
            import redis

            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                decode_responses=True,
                protocol=2,
                socket_connect_timeout=connect_timeout,
                socket_timeout=socket_timeout,
            )
            self.client.ping()
            self.backend = "redis"
            self.use_redis = True
            logger.info("Redis connected: %s:%s/%s", redis_host, redis_port, redis_db)
        except Exception as exc:
            self.client = SimpleCache()
            logger.warning(
                "Redis unavailable at %s:%s/%s, using SimpleCache: %s",
                redis_host,
                redis_port,
                redis_db,
                exc,
            )

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
        if hasattr(self.client, "lrem"):
            self.client.lrem(f"user:{user_id}:sessions", 0, session_id)
        self.client.lpush(f"user:{user_id}:sessions", session_id)
        self.client.ltrim(f"user:{user_id}:sessions", 0, 9)

    def get_user_sessions(self, user_id: str) -> List[str]:
        return self.client.lrange(f"user:{user_id}:sessions", 0, -1) or []

    def set_cache(self, key: str, value: str, ttl_seconds: int = 86400):
        self.client.set(key, value)
        self.client.expire(key, timedelta(seconds=ttl_seconds))

    def get_cache(self, key: str) -> Optional[str]:
        return self.client.get(key)
