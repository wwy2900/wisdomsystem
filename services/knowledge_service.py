"""Knowledge base management service."""
import os
import re
from typing import Iterable
from urllib.parse import quote

from rag.vector_store import VectorStoreService
from utils.config_handler import chroma_conf
from utils.knowledge_sources import iter_knowledge_source_files
from utils.path_tool import get_abs_path
from utils.logger_handler import logger


class KnowledgeService:
    """Manage knowledge files and vector-store chunks."""

    def __init__(self, upload_dir: str = "data/knowledge_uploads"):
        self.vector_store = VectorStoreService()
        self.upload_dir = get_abs_path(upload_dir)
        os.makedirs(self.upload_dir, exist_ok=True)
        logger.info("[KnowledgeService] 初始化完成")

    @property
    def allowed_extensions(self) -> set[str]:
        return {f".{ext.lstrip('.').lower()}" for ext in chroma_conf["allow_knowledge_file_type"]}

    def _safe_filename(self, filename: str) -> str:
        base_name = os.path.basename(filename).strip()
        name, ext = os.path.splitext(base_name)
        safe_name = re.sub(r"[^0-9A-Za-z_\-\u4e00-\u9fff]+", "_", name).strip("_")
        if not safe_name:
            safe_name = "knowledge"
        return f"{safe_name}{ext.lower()}"

    def _validate_extension(self, filename: str):
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.allowed_extensions:
            allowed = ", ".join(sorted(self.allowed_extensions))
            raise ValueError(f"Unsupported file type: {ext or 'none'}, allowed: {allowed}")

    def _safe_user_dir(self, user_id: str) -> str:
        return quote((user_id or "__shared__").strip() or "__shared__", safe="")

    def _iter_source_files(self) -> Iterable[tuple[str, str]]:
        yield from iter_knowledge_source_files(
            upload_dir=self.upload_dir,
            data_path=chroma_conf["data_path"],
            allowed_types=tuple(chroma_conf["allow_knowledge_file_type"]),
        )

    @staticmethod
    def _should_invalidate(result: dict | None) -> bool:
        return bool(result) and not result.get("skipped", False) and result.get("chunk_count", 0) > 0

    def _invalidate_rag_state(self):
        from rag.rag_service import RagSummarizeService

        RagSummarizeService().invalidate_knowledge_state()

    def add_uploaded_document(self, filename: str, content: bytes, user_id: str = "__shared__") -> dict:
        safe_name = self._safe_filename(filename)
        self._validate_extension(safe_name)

        upload_dir = os.path.join(self.upload_dir, self._safe_user_dir(user_id)) if user_id != "__shared__" else self.upload_dir
        os.makedirs(upload_dir, exist_ok=True)
        target_path = os.path.join(upload_dir, safe_name)
        with open(target_path, "wb") as f:
            f.write(content)

        result = self.vector_store.add_file(target_path, user_id=user_id)
        if self._should_invalidate(result):
            self._invalidate_rag_state()
        result["saved_path"] = target_path
        return result

    def add_document(self, file_path: str, user_id: str = "__shared__") -> dict:
        self._validate_extension(file_path)
        result = self.vector_store.add_file(file_path, user_id=user_id)
        if self._should_invalidate(result):
            self._invalidate_rag_state()
        return result

    def list_chunks(self, limit: int = 20, offset: int = 0, user_id: str | None = None) -> dict:
        return self.vector_store.list_chunks(limit=limit, offset=offset, user_id=user_id)

    def search_chunks(self, query: str, k: int = 5, user_id: str | None = None) -> list[dict]:
        return self.vector_store.search_chunks(query=query, k=k, user_id=user_id)

    def list_user_chunks(self, user_id: str, limit: int = 100, offset: int = 0) -> dict:
        return self.vector_store.list_user_chunks(user_id, limit=limit, offset=offset)

    def delete_chunk(self, doc_id: str, user_id: str | None = None) -> dict:
        before_total = self.vector_store.count_chunks(user_id=user_id)
        deleted = self.vector_store.delete_document(doc_id, user_id=user_id)
        after_total = before_total - 1 if deleted and before_total > 0 else before_total
        if deleted:
            self._invalidate_rag_state()
        return {
            "doc_id": doc_id,
            "deleted": deleted,
            "before_total": before_total,
            "after_total": after_total,
        }

    def rebuild(self) -> dict:
        self.vector_store.clear_collection()

        file_count = 0
        skipped_count = 0
        chunk_count = 0
        results = []

        for file_path, user_id in self._iter_source_files():
            file_count += 1
            result = self.vector_store.add_file(file_path, user_id=user_id)
            results.append(result)
            if result.get("skipped"):
                skipped_count += 1
            chunk_count += result.get("chunk_count", 0)

        self._invalidate_rag_state()

        return {
            "file_count": file_count,
            "skipped_count": skipped_count,
            "chunk_count": chunk_count,
            "results": results,
        }
