"""Authentication and role-scoped browser session management."""
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from database.sqlite_db import SQLiteDatabase
from utils.logger_handler import logger


class AuthError(Exception):
    """Raised when authentication fails."""


class UserConflictError(Exception):
    """Raised when a user cannot be created because of a uniqueness conflict."""


class UserValidationError(Exception):
    """Raised when submitted user data is invalid."""


class AuthService:
    def __init__(self, db: SQLiteDatabase | None = None):
        self.db = db or SQLiteDatabase()
        self.session_ttl_hours = int(os.getenv("AUTH_SESSION_TTL_HOURS", "24"))
        self.cookie_name = os.getenv("AUTH_SESSION_COOKIE_NAME", "wisdomsystem_session")
        self.cookie_secure = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}
        self.cookie_samesite = os.getenv("AUTH_COOKIE_SAMESITE", "lax")
        self._bootstrap_default_users()

    @staticmethod
    def _hash_password(password: str, salt_hex: str | None = None) -> str:
        salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(16)
        iterations = 390000
        derived_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return f"pbkdf2_sha256${iterations}${salt.hex()}${derived_key.hex()}"

    @classmethod
    def _verify_password(cls, password: str, stored_hash: str) -> bool:
        try:
            algorithm, iterations, salt_hex, expected_hash = stored_hash.split("$", 3)
        except ValueError:
            return False
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = cls._hash_password(password, salt_hex=salt_hex)
        return hmac.compare_digest(candidate, f"{algorithm}${iterations}${salt_hex}${expected_hash}")

    def _bootstrap_default_users(self):
        if self.db.count_users() > 0:
            return

        bootstrap_users = [
            {
                "username": os.getenv("AUTH_BOOTSTRAP_ADMIN_USERNAME", "admin"),
                "password": os.getenv("AUTH_BOOTSTRAP_ADMIN_PASSWORD", "Admin12345!"),
                "role": "admin",
                "display_name": os.getenv("AUTH_BOOTSTRAP_ADMIN_DISPLAY_NAME", "System Admin"),
            },
            {
                "username": os.getenv("AUTH_BOOTSTRAP_USER_USERNAME", "demo_user"),
                "password": os.getenv("AUTH_BOOTSTRAP_USER_PASSWORD", "User12345!"),
                "role": "user",
                "display_name": os.getenv("AUTH_BOOTSTRAP_USER_DISPLAY_NAME", "Demo User"),
            },
        ]

        for item in bootstrap_users:
            self.db.create_user(
                user_id=f"user_{uuid4().hex}",
                username=item["username"],
                password_hash=self._hash_password(item["password"]),
                role=item["role"],
                display_name=item["display_name"],
                is_active=True,
            )

        logger.warning(
            "[AuthService] Bootstrapped default users for browser login. Override AUTH_BOOTSTRAP_* in production."
        )

    @staticmethod
    def _public_user(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "display_name": user.get("display_name") or user["username"],
            "is_active": bool(user.get("is_active", True)),
        }

    @staticmethod
    def _user_summary(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "display_name": user.get("display_name") or user["username"],
            "is_active": bool(user.get("is_active", True)),
            "created_at": user["created_at"],
        }

    @staticmethod
    def _normalize_username(username: str) -> str:
        return username.strip()

    @staticmethod
    def _normalize_display_name(display_name: str) -> str:
        return display_name.strip()

    @staticmethod
    def _validate_password(password: str):
        if len(password) < 8:
            raise UserValidationError("Password must be at least 8 characters long")

    def _create_session_for_user(self, user: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        session_id = f"auth_{secrets.token_urlsafe(24)}"
        expires_at = (datetime.now() + timedelta(hours=self.session_ttl_hours)).isoformat()
        self.db.save_auth_session(session_id, user["id"], expires_at)
        return session_id, self._public_user(user)

    def create_user(self, username: str, password: str, display_name: str, role: str = "user") -> dict[str, Any]:
        normalized_username = self._normalize_username(username)
        normalized_display_name = self._normalize_display_name(display_name)

        if not normalized_username:
            raise UserValidationError("Username is required")
        if not normalized_display_name:
            raise UserValidationError("Display name is required")
        if role not in {"user", "admin"}:
            raise UserValidationError("Unsupported user role")

        self._validate_password(password)

        if self.db.get_user_by_username(normalized_username):
            raise UserConflictError("Username already exists")

        user = self.db.create_user(
            user_id=f"user_{uuid4().hex}",
            username=normalized_username,
            password_hash=self._hash_password(password),
            role=role,
            display_name=normalized_display_name,
            is_active=True,
        )
        return self._user_summary(user)

    def register_user(self, username: str, password: str, display_name: str) -> tuple[str, dict[str, Any]]:
        self.db.delete_expired_auth_sessions()
        self.create_user(username=username, password=password, display_name=display_name, role="user")
        user = self.db.get_user_by_username(self._normalize_username(username))
        if not user:
            raise UserValidationError("User registration failed")
        return self._create_session_for_user(user)

    def list_users(self) -> list[dict[str, Any]]:
        return [self._user_summary(user) for user in self.db.list_users()]

    def login(self, username: str, password: str) -> tuple[str, dict[str, Any]]:
        self.db.delete_expired_auth_sessions()
        user = self.db.get_user_by_username(self._normalize_username(username))
        if not user or not bool(user.get("is_active")):
            raise AuthError("Invalid username or password")
        if not self._verify_password(password, user["password_hash"]):
            raise AuthError("Invalid username or password")
        return self._create_session_for_user(user)

    def logout(self, session_id: str | None):
        if not session_id:
            return
        self.db.delete_auth_session(session_id)

    def get_current_user(self, session_id: str | None) -> dict[str, Any] | None:
        if not session_id:
            return None

        self.db.delete_expired_auth_sessions()
        session = self.db.get_auth_session(session_id)
        if not session:
            return None

        if session["expires_at"] <= datetime.now().isoformat():
            self.db.delete_auth_session(session_id)
            return None

        user = self.db.get_user_by_id(session["user_id"])
        if not user or not bool(user.get("is_active")):
            self.db.delete_auth_session(session_id)
            return None

        return self._public_user(user)
