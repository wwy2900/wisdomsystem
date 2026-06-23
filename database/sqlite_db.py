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

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS customer_devices (
                    device_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    serial_number TEXT,
                    status TEXT NOT NULL,
                    purchase_date TEXT,
                    warranty_expires_at TEXT,
                    is_default INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS device_consumables (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    consumable_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    remaining_percent INTEGER,
                    remaining_days INTEGER,
                    maintenance_tip TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (device_id) REFERENCES customer_devices(device_id)
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tool_audit_logs (
                    id TEXT PRIMARY KEY,
                    request_id TEXT,
                    session_id TEXT,
                    user_id TEXT,
                    tool_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    args_summary TEXT,
                    result_summary TEXT,
                    error_summary TEXT,
                    duration_ms INTEGER,
                    created_at TEXT NOT NULL
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

    @staticmethod
    def _row_to_customer_device(row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return {
            'device_id': row[0],
            'user_id': row[1],
            'product_name': row[2],
            'model': row[3],
            'serial_number': row[4],
            'status': row[5],
            'purchase_date': row[6],
            'warranty_expires_at': row[7],
            'is_default': bool(row[8]),
            'created_at': row[9],
            'updated_at': row[10],
        }

    @staticmethod
    def _row_to_device_consumable(row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return {
            'id': row[0],
            'device_id': row[1],
            'consumable_type': row[2],
            'status': row[3],
            'remaining_percent': row[4],
            'remaining_days': row[5],
            'maintenance_tip': row[6],
            'created_at': row[7],
            'updated_at': row[8],
        }

    @staticmethod
    def _row_to_tool_audit_log(row) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return {
            'id': row[0],
            'request_id': row[1],
            'session_id': row[2],
            'user_id': row[3],
            'tool_name': row[4],
            'status': row[5],
            'args_summary': row[6],
            'result_summary': row[7],
            'error_summary': row[8],
            'duration_ms': row[9],
            'created_at': row[10],
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

    def list_users(self) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, username, password_hash, role, display_name, is_active, created_at, updated_at
                FROM users
                ORDER BY created_at DESC, username ASC
            ''')
            return [self._row_to_user(row) for row in cursor.fetchall()]

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

    def upsert_customer_device(
        self,
        device_id: str,
        user_id: str,
        product_name: str,
        model: str,
        serial_number: str | None,
        status: str,
        purchase_date: str | None,
        warranty_expires_at: str | None,
        is_default: bool = False,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if is_default:
                cursor.execute('UPDATE customer_devices SET is_default = 0, updated_at = ? WHERE user_id = ?', (now, user_id))
            cursor.execute('''
                INSERT OR REPLACE INTO customer_devices
                (device_id, user_id, product_name, model, serial_number, status, purchase_date, warranty_expires_at, is_default, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM customer_devices WHERE device_id = ?), ?), ?)
            ''', (
                device_id,
                user_id,
                product_name,
                model,
                serial_number,
                status,
                purchase_date,
                warranty_expires_at,
                1 if is_default else 0,
                device_id,
                now,
                now,
            ))
            conn.commit()
        return self.get_customer_device(device_id=device_id, user_id=user_id)

    def list_customer_devices(self, user_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT device_id, user_id, product_name, model, serial_number, status, purchase_date, warranty_expires_at, is_default, created_at, updated_at
                FROM customer_devices
                WHERE user_id = ?
                ORDER BY is_default DESC, created_at ASC, device_id ASC
            ''', (user_id,))
            return [self._row_to_customer_device(row) for row in cursor.fetchall()]

    def get_customer_device(self, device_id: str, user_id: str | None = None) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if user_id is None:
                cursor.execute('''
                    SELECT device_id, user_id, product_name, model, serial_number, status, purchase_date, warranty_expires_at, is_default, created_at, updated_at
                    FROM customer_devices
                    WHERE device_id = ?
                ''', (device_id,))
            else:
                cursor.execute('''
                    SELECT device_id, user_id, product_name, model, serial_number, status, purchase_date, warranty_expires_at, is_default, created_at, updated_at
                    FROM customer_devices
                    WHERE device_id = ? AND user_id = ?
                ''', (device_id, user_id))
            return self._row_to_customer_device(cursor.fetchone())

    def upsert_device_consumable(
        self,
        record_id: str,
        device_id: str,
        consumable_type: str,
        status: str,
        remaining_percent: int | None,
        remaining_days: int | None,
        maintenance_tip: str | None,
    ) -> Dict[str, Any]:
        now = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO device_consumables
                (id, device_id, consumable_type, status, remaining_percent, remaining_days, maintenance_tip, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM device_consumables WHERE id = ?), ?), ?)
            ''', (
                record_id,
                device_id,
                consumable_type,
                status,
                remaining_percent,
                remaining_days,
                maintenance_tip,
                record_id,
                now,
                now,
            ))
            conn.commit()
        return self.get_device_consumable(record_id)

    def get_device_consumable(self, record_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, device_id, consumable_type, status, remaining_percent, remaining_days, maintenance_tip, created_at, updated_at
                FROM device_consumables
                WHERE id = ?
            ''', (record_id,))
            return self._row_to_device_consumable(cursor.fetchone())

    def list_device_consumables(self, device_id: str) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, device_id, consumable_type, status, remaining_percent, remaining_days, maintenance_tip, created_at, updated_at
                FROM device_consumables
                WHERE device_id = ?
                ORDER BY consumable_type ASC, created_at ASC
            ''', (device_id,))
            return [self._row_to_device_consumable(row) for row in cursor.fetchall()]

    def create_tool_audit_log(
        self,
        log_id: str,
        request_id: str | None,
        session_id: str | None,
        user_id: str | None,
        tool_name: str,
        status: str,
        args_summary: str | None = None,
        result_summary: str | None = None,
        error_summary: str | None = None,
        duration_ms: int | None = None,
    ) -> Dict[str, Any]:
        created_at = datetime.now().isoformat()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tool_audit_logs
                (id, request_id, session_id, user_id, tool_name, status, args_summary, result_summary, error_summary, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                log_id,
                request_id,
                session_id,
                user_id,
                tool_name,
                status,
                args_summary,
                result_summary,
                error_summary,
                duration_ms,
                created_at,
            ))
            conn.commit()
        return self.get_tool_audit_log(log_id)

    def get_tool_audit_log(self, log_id: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, request_id, session_id, user_id, tool_name, status, args_summary, result_summary, error_summary, duration_ms, created_at
                FROM tool_audit_logs
                WHERE id = ?
            ''', (log_id,))
            return self._row_to_tool_audit_log(cursor.fetchone())

    def list_tool_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, request_id, session_id, user_id, tool_name, status, args_summary, result_summary, error_summary, duration_ms, created_at
                FROM tool_audit_logs
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            return [self._row_to_tool_audit_log(row) for row in cursor.fetchall()]
