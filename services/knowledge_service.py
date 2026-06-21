"""Knowledge base management service."""
import os
import re
from typing import Iterable

from rag.vector_store import VectorStoreService
from utils.config_handler import chroma_conf
from utils.file_handler import listdir_with_allowed_type
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

    def _iter_source_files(self) -> Iterable[str]:
        allowed_types = tuple(chroma_conf["allow_knowledge_file_type"])
        data_files = listdir_with_allowed_type(get_abs_path(chroma_conf["data_path"]), allowed_types)
        upload_files = listdir_with_allowed_type(self.upload_dir, allowed_types)
        seen = set()
        for path in list(data_files) + list(upload_files):
            abs_path = os.path.abspath(path)
            if abs_path in seen:
                continue
            seen.add(abs_path)
            yield path

    def add_uploaded_document(self, filename: str, content: bytes) -> dict:
        safe_name = self._safe_filename(filename)
        self._validate_extension(safe_name)

        target_path = os.path.join(self.upload_dir, safe_name)
        with open(target_path, "wb") as f:
            f.write(content)

        result = self.vector_store.add_file(target_path)
        result["saved_path"] = target_path
        return result

    def add_document(self, file_path: str) -> dict:
        self._validate_extension(file_path)
        return self.vector_store.add_file(file_path)

    def list_chunks(self, limit: int = 20, offset: int = 0) -> dict:
        return self.vector_store.list_chunks(limit=limit, offset=offset)

    def search_chunks(self, query: str, k: int = 5) -> list[dict]:
        return self.vector_store.search_chunks(query=query, k=k)

    def delete_chunk(self, doc_id: str) -> dict:
        before_total = self.vector_store.list_chunks(limit=1, offset=0)["total"]
        self.vector_store.delete_document(doc_id)
        after_total = self.vector_store.list_chunks(limit=1, offset=0)["total"]
        return {
            "doc_id": doc_id,
            "deleted": after_total < before_total,
            "before_total": before_total,
            "after_total": after_total,
        }

    def rebuild(self) -> dict:
        self.vector_store.clear_collection()

        file_count = 0
        skipped_count = 0
        chunk_count = 0
        results = []

        for file_path in self._iter_source_files():
            file_count += 1
            result = self.vector_store.add_file(file_path)
            results.append(result)
            if result.get("skipped"):
                skipped_count += 1
            chunk_count += result.get("chunk_count", 0)

        return {
            "file_count": file_count,
            "skipped_count": skipped_count,
            "chunk_count": chunk_count,
            "results": results,
        }
