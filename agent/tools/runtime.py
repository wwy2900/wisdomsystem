from __future__ import annotations

import json
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from database.sqlite_db import SQLiteDatabase
from utils.logger_handler import logger


@dataclass
class SourceReference:
    source_type: str
    title: str
    snippet: str
    tool_name: str
    doc_id: str | None = None
    record_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def dedupe_key(self) -> str:
        return json.dumps(
            {
                "source_type": self.source_type,
                "tool_name": self.tool_name,
                "doc_id": self.doc_id,
                "record_id": self.record_id,
                "title": self.title,
            },
            ensure_ascii=False,
            sort_keys=True,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_type": self.source_type,
            "title": self.title,
            "snippet": self.snippet,
            "tool_name": self.tool_name,
            "doc_id": self.doc_id,
            "record_id": self.record_id,
            "metadata": self.metadata,
        }


@dataclass
class RequestRuntimeContext:
    request_id: str
    user_id: str
    session_id: str
    sources: list[SourceReference] = field(default_factory=list)
    _source_keys: set[str] = field(default_factory=set, repr=False)

    def add_source(self, source: SourceReference):
        key = source.dedupe_key()
        if key in self._source_keys:
            return
        self._source_keys.add(key)
        self.sources.append(source)


_request_context: ContextVar[RequestRuntimeContext | None] = ContextVar("tool_request_context", default=None)


def start_request_context(user_id: str, session_id: str) -> Any:
    context = RequestRuntimeContext(
        request_id=f"req_{uuid4().hex}",
        user_id=user_id,
        session_id=session_id,
    )
    return _request_context.set(context)


def reset_request_context(token: Any):
    _request_context.reset(token)


def get_request_context() -> RequestRuntimeContext | None:
    return _request_context.get()


def get_request_user_id() -> str | None:
    context = get_request_context()
    return context.user_id if context else None


def add_source_reference(source: SourceReference):
    context = get_request_context()
    if not context:
        return
    context.add_source(source)


def get_source_references() -> list[dict[str, Any]]:
    context = get_request_context()
    if not context:
        return []
    return [source.to_dict() for source in context.sources]


def summarize_value(value: Any, max_length: int = 320) -> str:
    if isinstance(value, str):
        serialized = value
    else:
        try:
            serialized = json.dumps(value, ensure_ascii=False, sort_keys=True)
        except TypeError:
            serialized = str(value)

    if len(serialized) <= max_length:
        return serialized
    return f"{serialized[:max_length]}..."


def create_tool_audit_log(
    tool_name: str,
    status: str,
    args: dict[str, Any] | None = None,
    result: Any = None,
    error: Exception | None = None,
    duration_ms: int | None = None,
):
    context = get_request_context()
    request_id = context.request_id if context else None
    session_id = context.session_id if context else None
    user_id = context.user_id if context else None

    try:
        SQLiteDatabase().create_tool_audit_log(
            log_id=f"audit_{uuid4().hex}",
            request_id=request_id,
            session_id=session_id,
            user_id=user_id,
            tool_name=tool_name,
            status=status,
            args_summary=summarize_value(args or {}),
            result_summary=summarize_value(result) if result is not None else None,
            error_summary=summarize_value(str(error)) if error else None,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        logger.warning(f"[tool_audit] failed to persist audit log for {tool_name}: {str(exc)}")


def run_audited_tool(tool_name: str, args: dict[str, Any], callback: Callable[[], Any]):
    started_at = time.perf_counter()
    try:
        result = callback()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        create_tool_audit_log(
            tool_name=tool_name,
            status="success",
            args=args,
            result=result,
            duration_ms=duration_ms,
        )
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        create_tool_audit_log(
            tool_name=tool_name,
            status="failed",
            args=args,
            error=exc,
            duration_ms=duration_ms,
        )
        raise
