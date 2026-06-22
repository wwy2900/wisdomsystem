import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from utils.logger_handler import logger


# 单例模式：避免重复初始化数据库连接
_instance = None


class SQLiteDatabase:
    def __new__(cls, db_path: str = "data/memory.db"):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self, db_path: str = "data/memory.db"):
        if self._initialized:
            return
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_tables()
        self._initialized = True

    def _safe_json_parse(self, value: str, default=None):
        """安全解析JSON字符串，失败时返回默认值并记录日志"""
        if not value:
            return default
        
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            # 尝试兼容旧格式（eval格式）
            try:
                import ast
                result = ast.literal_eval(value)
                logger.warning(f"[SQLite] 检测到旧格式数据，已自动迁移: {value[:50]}...")
                return result
            except (SyntaxError, ValueError):
                logger.error(f"[SQLite] JSON解析失败，值: {value[:50]}...")
                return default

    def _init_tables(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    occupation TEXT,
                    preferences TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    summary_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    session_id TEXT,
                    keywords TEXT,
                    topics TEXT,
                    summary_text TEXT,
                    created_at TEXT
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    display_name TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            conn.commit()

    def _row_to_user(self, row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return {
            'id': row[0],
            'username': row[1],
            'password_hash': row[2],
            'role': row[3],
            'display_name': row[4],
            'is_active': bool(row[5]),
            'created_at': row[6],
            'updated_at': row[7],
        }

    def save_user_profile(self, user_id: str, data: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_profiles 
                (user_id, name, occupation, preferences, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                data.get('name'),
                data.get('occupation'),
                json.dumps(data.get('preferences', {}), ensure_ascii=False),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM user_profiles WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'user_id': row[0],
                    'name': row[1],
                    'occupation': row[2],
                    'preferences': self._safe_json_parse(row[3], {}),
                    'created_at': row[4],
                    'updated_at': row[5]
                }
            return None

    def save_conversation_summary(self, summary_id: str, user_id: str, session_id: str,
                                   keywords: List[str], topics: List[str], summary_text: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO conversation_summaries
                (summary_id, user_id, session_id, keywords, topics, summary_text, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary_id,
                user_id,
                session_id,
                json.dumps(keywords, ensure_ascii=False),
                json.dumps(topics, ensure_ascii=False),
                summary_text,
                datetime.now().isoformat()
            ))
            conn.commit()

    def get_user_summaries(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM conversation_summaries 
                WHERE user_id = ? 
                ORDER BY created_at DESC LIMIT ?
            ''', (user_id, limit))
            rows = cursor.fetchall()
            return [{
                'summary_id': row[0],
                'user_id': row[1],
                'session_id': row[2],
                'keywords': self._safe_json_parse(row[3], []),
                'topics': self._safe_json_parse(row[4], []),
                'summary_text': row[5],
                'created_at': row[6]
            } for row in rows]

    def count_users(self) -> int:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def create_user(
        self,
        user_id: str,
        username: str,
        password_hash: str,
        role: str,
        display_name: Optional[str] = None,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO users
                (id, username, password_hash, role, display_name, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                username,
                password_hash,
                role,
                display_name,
                1 if is_active else 0,
                now,
                now,
            ))
            conn.commit()
        return self.get_user_by_id(user_id)

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, role, display_name, is_active, created_at, updated_at
                FROM users
                WHERE username = ?
            ''', (username,))
            return self._row_to_user(cursor.fetchone())

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, role, display_name, is_active, created_at, updated_at
                FROM users
                WHERE id = ?
            ''', (user_id,))
            return self._row_to_user(cursor.fetchone())

    def save_auth_session(self, session_id: str, user_id: str, expires_at: str) -> Dict[str, Any]:
        created_at = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO auth_sessions
                (session_id, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?)
            ''', (session_id, user_id, expires_at, created_at))
            conn.commit()
        return self.get_auth_session(session_id)

    def get_auth_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id, user_id, expires_at, created_at
                FROM auth_sessions
                WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                'session_id': row[0],
                'user_id': row[1],
                'expires_at': row[2],
                'created_at': row[3],
            }

    def delete_auth_session(self, session_id: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM auth_sessions WHERE session_id = ?', (session_id,))
            conn.commit()

    def delete_expired_auth_sessions(self, now_iso: Optional[str] = None):
        cutoff = now_iso or datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM auth_sessions WHERE expires_at <= ?', (cutoff,))
            conn.commit()
