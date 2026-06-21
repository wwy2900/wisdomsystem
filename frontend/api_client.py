"""HTTP client used by the Streamlit frontend."""
import json
import os
from collections.abc import Generator
from typing import Any

import requests


class ApiClientError(Exception):
    """Raised when the FastAPI backend returns an error or is unavailable."""


class ApiClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None, timeout: int = 30):
        self.base_url = (base_url or os.getenv("FASTAPI_BASE_URL") or "http://localhost:8000").rstrip("/")
        self.api_key = api_key if api_key is not None else os.getenv("FASTAPI_API_KEY", "")
        self.timeout = timeout

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, **kwargs) -> Any:
        headers = kwargs.pop("headers", {})
        merged_headers = self._headers()
        merged_headers.update(headers)
        try:
            response = requests.request(
                method,
                self._url(path),
                headers=merged_headers,
                timeout=kwargs.pop("timeout", self.timeout),
                **kwargs,
            )
        except requests.RequestException as e:
            raise ApiClientError("后端不可用，请先启动 FastAPI") from e

        if response.status_code >= 400:
            raise ApiClientError(self._error_message(response))

        if not response.content:
            return None
        return response.json()

    def _error_message(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or f"HTTP {response.status_code}"
        detail = payload.get("detail", payload)
        if isinstance(detail, list):
            return json.dumps(detail, ensure_ascii=False)
        return str(detail)

    def health(self) -> dict:
        return self._request("GET", "/health")

    def create_session(self, user_id: str) -> str:
        data = self._request("POST", "/api/v1/sessions", json={"user_id": user_id})
        return data["session_id"]

    def list_user_sessions(self, user_id: str) -> list[dict]:
        data = self._request("GET", f"/api/v1/users/{user_id}/sessions")
        return data.get("sessions", [])

    def get_session(self, session_id: str) -> dict | None:
        try:
            return self._request("GET", f"/api/v1/sessions/{session_id}")
        except ApiClientError as e:
            if "Session not found" in str(e):
                return None
            raise

    def stream_chat(
        self,
        user_id: str,
        message: str,
        session_id: str | None = None,
    ) -> Generator[tuple[str, dict], None, None]:
        payload = {"user_id": user_id, "message": message, "session_id": session_id}
        headers = self._headers()
        headers["Accept"] = "text/event-stream"
        try:
            with requests.post(
                self._url("/api/v1/chat/stream"),
                json=payload,
                headers=headers,
                timeout=None,
                stream=True,
            ) as response:
                if response.status_code >= 400:
                    raise ApiClientError(self._error_message(response))
                yield from self._iter_sse(response)
        except requests.RequestException as e:
            raise ApiClientError("后端不可用，请先启动 FastAPI") from e

    def _iter_sse(self, response: requests.Response) -> Generator[tuple[str, dict], None, None]:
        event_name = "message"
        data_lines: list[str] = []

        for raw_line in response.iter_lines(decode_unicode=True):
            if raw_line is None:
                continue
            line = raw_line.strip("\r")
            if not line:
                if data_lines:
                    data_text = "\n".join(data_lines)
                    try:
                        payload = json.loads(data_text)
                    except json.JSONDecodeError:
                        payload = {"content": data_text}
                    yield event_name, payload
                event_name = "message"
                data_lines = []
                continue

            if line.startswith("event:"):
                event_name = line[len("event:"):].strip()
            elif line.startswith("data:"):
                data_lines.append(line[len("data:"):].strip())

    def upload_document(self, file_name: str, content: bytes, user_id: str = "__shared__") -> dict:
        files = {"file": (file_name, content)}
        headers = self._headers()
        headers.pop("Accept", None)
        return self._request("POST", f"/api/v1/knowledge/documents/upload?user_id={user_id}", files=files, headers=headers, timeout=120)

    def list_chunks(self, limit: int = 20, offset: int = 0, user_id: str | None = None) -> dict:
        params = {"limit": limit, "offset": offset}
        if user_id:
            params["user_id"] = user_id
        return self._request("GET", "/api/v1/knowledge/chunks", params=params)

    def search_chunks(self, query: str, k: int = 5, user_id: str | None = None) -> list[dict]:
        params = {"query": query, "k": k}
        if user_id:
            params["user_id"] = user_id
        data = self._request("GET", "/api/v1/knowledge/search", params=params)
        return data.get("results", [])

    def delete_chunk(self, doc_id: str, user_id: str | None = None) -> dict:
        params = {}
        if user_id:
            params["user_id"] = user_id
        return self._request("DELETE", f"/api/v1/knowledge/chunks/{doc_id}", params=params)

    def list_user_chunks(self, user_id: str, limit: int = 100, offset: int = 0) -> dict:
        return self._request("GET", f"/api/v1/knowledge/users/{user_id}/chunks", params={"limit": limit, "offset": offset})

    def rebuild_knowledge(self) -> dict:
        return self._request("POST", "/api/v1/knowledge/rebuild", timeout=300)
