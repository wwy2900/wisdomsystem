import io
import os
import sys
import tempfile
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from fastapi.testclient import TestClient

import database.sqlite_db as sqlite_db_module


sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


class FakeChatService:
    def __init__(self):
        self.sessions = {}

    def create_session(self, user_id: str) -> str:
        session_id = f"session_{len(self.sessions) + 1}"
        self.sessions[session_id] = {
            "session_id": session_id,
            "user_id": user_id,
            "messages": [],
            "saved_at": "2026-06-22T00:00:00",
        }
        return session_id

    def list_user_sessions(self, user_id: str) -> list[dict]:
        sessions = [item for item in self.sessions.values() if item["user_id"] == user_id]
        return [
            {
                "session_id": item["session_id"],
                "preview": item["messages"][-1]["content"][:30] if item["messages"] else "empty",
                "saved_at": item["saved_at"],
            }
            for item in sessions
        ]

    def get_session(self, session_id: str) -> dict | None:
        return self.sessions.get(session_id)

    def get_user_session(self, session_id: str, user_id: str) -> dict | None:
        session = self.get_session(session_id)
        if not session or session["user_id"] != user_id:
            return None
        return session

    def chat_stream(self, user_id: str, session_id: str, message: str):
        session = self.sessions.setdefault(
            session_id,
            {
                "session_id": session_id,
                "user_id": user_id,
                "messages": [],
                "saved_at": "2026-06-22T00:00:00",
            },
        )
        session["messages"].append({"role": "user", "content": message})
        sources = [
            {
                "source_type": "knowledge",
                "title": "faq.md",
                "snippet": "reply source",
                "tool_name": "rag_summarize",
                "doc_id": "doc_1",
                "record_id": None,
                "metadata": {"source_file": "faq.md", "page": 1},
            }
        ]
        yield ("tool_event", {"content": "[TOOL]mock_lookup"})
        yield ("answer_delta", {"content": "reply-1 "})
        yield ("answer_delta", {"content": "reply-2"})
        session["messages"].append({"role": "assistant", "content": "reply-1 reply-2", "sources": sources})
        yield ("_done", {"sources": sources})


class FakeKnowledgeService:
    def __init__(self):
        self.counter = 0
        self.chunks = []

    def add_uploaded_document(self, filename: str, content: bytes, user_id: str = "__shared__") -> dict:
        self.counter += 1
        doc_id = f"doc_{self.counter}"
        record = {
            "doc_id": doc_id,
            "content": content.decode("utf-8", errors="ignore") or filename,
            "metadata": {"user_id": user_id, "source_file": filename},
        }
        self.chunks.append(record)
        return {
            "file_name": filename,
            "md5": f"md5_{self.counter}",
            "skipped": False,
            "reason": "",
            "chunk_count": 1,
            "chunk_ids": [doc_id],
            "saved_path": None,
        }

    def list_user_chunks(self, user_id: str, limit: int = 100, offset: int = 0) -> dict:
        items = [item for item in self.chunks if item["metadata"]["user_id"] == user_id]
        return {"total": len(items), "limit": limit, "offset": offset, "chunks": items[offset:offset + limit]}

    def list_chunks(self, limit: int = 20, offset: int = 0, user_id: str | None = None) -> dict:
        items = self.chunks
        if user_id is not None:
            items = [item for item in items if item["metadata"]["user_id"] == user_id]
        return {"total": len(items), "limit": limit, "offset": offset, "chunks": items[offset:offset + limit]}

    def search_chunks(self, query: str, k: int = 5, user_id: str | None = None) -> list[dict]:
        items = self.chunks
        if user_id is not None:
            items = [item for item in items if item["metadata"]["user_id"] == user_id]
        matches = [item for item in items if query.lower() in item["content"].lower()]
        return matches[:k]

    def delete_chunk(self, doc_id: str, user_id: str | None = None) -> dict:
        before_total = len(self.chunks)
        deleted = False
        remaining = []
        for item in self.chunks:
            if item["doc_id"] == doc_id and (user_id is None or item["metadata"]["user_id"] == user_id) and not deleted:
                deleted = True
                continue
            remaining.append(item)
        self.chunks = remaining
        after_total = len(self.chunks)
        return {
            "doc_id": doc_id,
            "deleted": deleted,
            "before_total": before_total,
            "after_total": after_total,
        }

    def rebuild(self) -> dict:
        self.chunks = [item for item in self.chunks if item["metadata"]["user_id"] != "__shared__"]
        return {"file_count": 0, "skipped_count": 0, "chunk_count": len(self.chunks), "results": []}


class ApiAuthTests(unittest.TestCase):
    def setUp(self):
        sqlite_db_module._instance = None

    @contextmanager
    def make_client(self):
        temp_dir = tempfile.mkdtemp(prefix="wisdomsystem-auth-")
        db_path = os.path.join(temp_dir, "auth.db")
        os.environ["AUTH_BOOTSTRAP_ADMIN_PASSWORD"] = "Admin12345!"
        os.environ["AUTH_BOOTSTRAP_USER_PASSWORD"] = "User12345!"
        from database.sqlite_db import SQLiteDatabase
        from services.auth_service import AuthService
        from api.main import app

        auth_service = AuthService(db=SQLiteDatabase(db_path=db_path))
        with patch("api.main.build_chat_service", return_value=FakeChatService()), patch(
            "api.main.build_knowledge_service",
            return_value=FakeKnowledgeService(),
        ), patch("api.main.build_auth_service", return_value=auth_service):
            with TestClient(app) as client:
                yield client

    def login(self, client: TestClient, username: str, password: str):
        return client.post("/api/v1/auth/login", json={"username": username, "password": password})

    def test_login_and_me_restore_cookie_session(self):
        with self.make_client() as client:
            response = self.login(client, "demo_user", "User12345!")
            self.assertEqual(response.status_code, 200)
            me_response = client.get("/api/v1/auth/me")
            self.assertEqual(me_response.status_code, 200)
            self.assertEqual(me_response.json()["username"], "demo_user")

    def test_register_creates_user_and_restores_cookie_session(self):
        with self.make_client() as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "alice",
                    "password": "Password123",
                    "display_name": "Alice",
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertIn("set-cookie", response.headers)
            self.assertEqual(response.json()["user"]["role"], "user")

            me_response = client.get("/api/v1/auth/me")
            self.assertEqual(me_response.status_code, 200)
            self.assertEqual(me_response.json()["username"], "alice")

    def test_register_rejects_duplicate_username(self):
        with self.make_client() as client:
            response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": "demo_user",
                    "password": "Password123",
                    "display_name": "Duplicate",
                },
            )
            self.assertEqual(response.status_code, 409)

    def test_requires_auth_for_me_routes(self):
        with self.make_client() as client:
            response = client.get("/api/v1/me/sessions")
            self.assertEqual(response.status_code, 401)

    def test_user_cannot_access_admin_routes(self):
        with self.make_client() as client:
            self.login(client, "demo_user", "User12345!")
            response = client.get("/api/v1/admin/knowledge/chunks")
            self.assertEqual(response.status_code, 403)

    def test_admin_can_access_admin_routes(self):
        with self.make_client() as client:
            self.login(client, "admin", "Admin12345!")
            response = client.get("/api/v1/admin/knowledge/chunks")
            self.assertEqual(response.status_code, 200)
            self.assertIn("chunks", response.json())

    def test_user_cannot_access_admin_user_routes(self):
        with self.make_client() as client:
            self.login(client, "demo_user", "User12345!")
            response = client.get("/api/v1/admin/users")
            self.assertEqual(response.status_code, 403)

    def test_admin_can_list_and_create_users(self):
        with self.make_client() as client:
            self.login(client, "admin", "Admin12345!")

            list_response = client.get("/api/v1/admin/users")
            self.assertEqual(list_response.status_code, 200)
            self.assertGreaterEqual(len(list_response.json()["users"]), 2)

            create_response = client.post(
                "/api/v1/admin/users",
                json={
                    "username": "operator",
                    "password": "Password123",
                    "display_name": "Operator",
                    "role": "admin",
                },
            )
            self.assertEqual(create_response.status_code, 200)
            self.assertEqual(create_response.json()["role"], "admin")

            refreshed = client.get("/api/v1/admin/users")
            usernames = [item["username"] for item in refreshed.json()["users"]]
            self.assertIn("operator", usernames)

    def test_user_cannot_read_other_users_session(self):
        with self.make_client() as client:
            self.login(client, "demo_user", "User12345!")
            create_response = client.post("/api/v1/me/sessions")
            session_id = create_response.json()["session_id"]
            client.post("/api/v1/auth/logout")

            self.login(client, "admin", "Admin12345!")
            response = client.get(f"/api/v1/me/sessions/{session_id}")
            self.assertEqual(response.status_code, 404)

    def test_user_cannot_delete_other_users_private_chunk(self):
        with self.make_client() as client:
            self.login(client, "demo_user", "User12345!")
            upload_response = client.post(
                "/api/v1/me/knowledge/documents/upload",
                files={"file": ("notes.txt", b"user-private")},
            )
            doc_id = upload_response.json()["chunk_ids"][0]
            client.post("/api/v1/auth/logout")

            self.login(client, "admin", "Admin12345!")
            response = client.delete(f"/api/v1/me/knowledge/chunks/{doc_id}")
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()["deleted"])

    def test_me_chat_stream_emits_expected_events(self):
        with self.make_client() as client:
            self.login(client, "demo_user", "User12345!")
            with client.stream("POST", "/api/v1/me/chat/stream", json={"message": "hello"}) as response:
                body = "".join(chunk.decode("utf-8") for chunk in response.iter_bytes())
            self.assertEqual(response.status_code, 200)
            self.assertIn("event: session", body)
            self.assertIn("event: tool_event", body)
            self.assertIn("event: answer_delta", body)
            self.assertIn("event: done", body)
            self.assertIn('"sources":', body)

    def test_session_detail_returns_assistant_sources(self):
        with self.make_client() as client:
            self.login(client, "demo_user", "User12345!")
            create_response = client.post("/api/v1/me/sessions")
            session_id = create_response.json()["session_id"]
            with client.stream("POST", "/api/v1/me/chat/stream", json={"message": "hello", "session_id": session_id}) as response:
                _ = "".join(chunk.decode("utf-8") for chunk in response.iter_bytes())
            self.assertEqual(response.status_code, 200)

            detail_response = client.get(f"/api/v1/me/sessions/{session_id}")
            self.assertEqual(detail_response.status_code, 200)
            assistant_messages = [item for item in detail_response.json()["messages"] if item["role"] == "assistant"]
            self.assertEqual(len(assistant_messages), 1)
            self.assertEqual(assistant_messages[0]["sources"][0]["title"], "faq.md")


if __name__ == "__main__":
    unittest.main()
