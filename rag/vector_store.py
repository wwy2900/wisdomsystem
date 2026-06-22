import hashlib
import json
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote

from langchain_chroma import Chroma
from langchain_core.documents import Document

from model.factory import embed_model
from rag.document_identity import get_document_identity
from rag.document_parsers import DocumentParserFactory
from rag.question_splitter import QuestionBasedSplitter
from utils.config_handler import chroma_conf
from utils.file_handler import get_file_md5_hex, listdir_with_allowed_type
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


class VectorStoreService:
    _md5_store_lock = threading.Lock()

    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"],
        )
        self.spliter = QuestionBasedSplitter()
        self.batch_size = 10

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": 10})

    def _get_md5_path(self) -> str:
        return get_abs_path(chroma_conf["md5_hex_store"])

    def _empty_md5_store(self) -> dict:
        return {"version": 1, "records": {}}

    def _ensure_md5_store(self):
        md5_path = self._get_md5_path()
        md5_dir = os.path.dirname(md5_path)
        if md5_dir:
            os.makedirs(md5_dir, exist_ok=True)
        if not os.path.exists(md5_path):
            self._write_md5_store(self._empty_md5_store())

    def _md5_scope(self, user_id: str | None = None) -> str:
        return quote((user_id or "__shared__").strip() or "__shared__", safe="")

    def _md5_record(self, md5_hex: str, user_id: str | None = None) -> str:
        return f"{self._md5_scope(user_id)}:{md5_hex}"

    def _read_md5_store(self) -> dict:
        self._ensure_md5_store()
        md5_path = self._get_md5_path()

        with open(md5_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()

        if not raw_text:
            return self._empty_md5_store()

        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            payload = None

        if isinstance(payload, dict):
            version = payload.get("version", 1)
            raw_records = payload.get("records", payload)
            records = {}
            if isinstance(raw_records, dict):
                for scope, md5_values in raw_records.items():
                    if isinstance(md5_values, list):
                        records[scope] = sorted({str(value) for value in md5_values if value})
            return {"version": version, "records": records}

        records = {}
        for line in raw_text.splitlines():
            record = line.strip()
            if not record:
                continue
            if ":" in record:
                scope, md5_hex = record.split(":", 1)
            else:
                scope, md5_hex = "__shared__", record
            if md5_hex:
                records.setdefault(scope, set()).add(md5_hex)

        return {
            "version": 1,
            "records": {scope: sorted(values) for scope, values in records.items()},
        }

    def _write_md5_store(self, payload: dict):
        md5_path = self._get_md5_path()
        temp_path = f"{md5_path}.tmp"
        normalized_payload = {
            "version": payload.get("version", 1),
            "records": {
                scope: sorted({str(value) for value in values if value})
                for scope, values in payload.get("records", {}).items()
            },
        }
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(normalized_payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(temp_path, md5_path)

    def _check_file_exists(self, md5_for_check: str, user_id: str = "__shared__") -> bool:
        with self._md5_store_lock:
            payload = self._read_md5_store()
            scope = self._md5_scope(user_id)
            return md5_for_check in set(payload["records"].get(scope, []))

    def _save_file_md5(self, md5_for_save: str, user_id: str = "__shared__"):
        with self._md5_store_lock:
            payload = self._read_md5_store()
            scope = self._md5_scope(user_id)
            records = payload["records"].setdefault(scope, [])
            if md5_for_save not in records:
                records.append(md5_for_save)
            self._write_md5_store(payload)

    @staticmethod
    def _content_md5(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _build_chunk_id(self, doc: Document, chunk_index: int, user_id: str) -> str:
        metadata = doc.metadata or {}
        identity_payload = {
            "user_id": user_id,
            "file_md5": metadata.get("file_md5", ""),
            "source_path": metadata.get("source_path") or metadata.get("source", ""),
            "chunk_index": chunk_index,
            "page": metadata.get("page"),
            "section_path": metadata.get("section_path", ""),
            "table_index": metadata.get("table_index"),
            "content_type": metadata.get("content_type", ""),
            "json_path": metadata.get("json_path", ""),
            "record_index": metadata.get("record_index"),
            "sheet_name": metadata.get("sheet_name", ""),
            "row_index": metadata.get("row_index"),
            "markdown_path": metadata.get("markdown_path", ""),
            "content_md5": self._content_md5(doc.page_content),
        }
        encoded_identity = json.dumps(identity_payload, ensure_ascii=False, sort_keys=True)
        return f"chunk_{uuid.uuid5(uuid.NAMESPACE_URL, encoded_identity).hex}"

    @staticmethod
    def _build_where(user_id: str | None = None, doc_id: str | None = None) -> dict | None:
        where = {}
        if user_id is not None:
            where["user_id"] = user_id
        if doc_id is not None:
            where["doc_id"] = doc_id
        return where or None

    @staticmethod
    def _result_to_chunks(result: dict) -> list[dict]:
        ids = result.get("ids") or []
        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        chunks = []

        for index, vector_id in enumerate(ids):
            metadata = metadatas[index] if index < len(metadatas) and metadatas else {}
            content = documents[index] if index < len(documents) and documents else ""
            chunks.append(
                {
                    "vector_id": vector_id,
                    "doc_id": metadata.get("doc_id", vector_id),
                    "content": content,
                    "metadata": metadata,
                }
            )
        return chunks

    def _count_where(self, where: dict | None = None) -> int:
        return len(self.vector_store.get(where=where, include=[])["ids"])

    def count_chunks(self, user_id: str | None = None) -> int:
        return self._count_where(self._build_where(user_id=user_id))

    def _batch_add_documents(self, documents: list[Document], user_id: str = "__shared__") -> list[str]:
        added_doc_ids = []
        for start in range(0, len(documents), self.batch_size):
            batch = documents[start:start + self.batch_size]
            batch_ids = []
            for chunk_index, doc in enumerate(batch, start=start):
                doc_id = self._build_chunk_id(doc, chunk_index, user_id)
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["doc_id"] = doc_id
                doc.metadata["user_id"] = user_id
                batch_ids.append(doc_id)
                added_doc_ids.append(doc_id)
            self.vector_store.add_documents(batch, ids=batch_ids)
        return added_doc_ids

    def add_file(self, file_path: str, user_id: str = "__shared__") -> dict:
        allowed_types = tuple(f".{t.lstrip('.')}" for t in chroma_conf["allow_knowledge_file_type"])
        if not file_path.lower().endswith(allowed_types):
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": None,
                "skipped": True,
                "reason": "unsupported_file_type",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        md5_hex = get_file_md5_hex(file_path)
        if not md5_hex:
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": None,
                "skipped": True,
                "reason": "md5_failed",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        if self._check_file_exists(md5_hex, user_id=user_id):
            logger.info(f"[鍔犺浇鐭ヨ瘑搴揮]鍐呭宸茬粡瀛樺湪锛岃烦杩? {file_path}")
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": md5_hex,
                "skipped": True,
                "reason": "duplicate_md5",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        documents = DocumentParserFactory.parse(file_path)
        if not documents:
            logger.warning(f"[鍔犺浇鐭ヨ瘑搴揮]鏂囨。鏃犳湁鏁堝唴瀹癸紝璺宠繃: {file_path}")
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": md5_hex,
                "skipped": True,
                "reason": "empty_document",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        split_documents = self.spliter.split_documents(documents)
        if not split_documents:
            logger.warning(f"[鍔犺浇鐭ヨ瘑搴揮]鍒嗙墖鍚庢棤鍐呭锛岃烦杩? {file_path}")
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": md5_hex,
                "skipped": True,
                "reason": "empty_chunks",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        for doc in split_documents:
            if not doc.metadata:
                doc.metadata = {}
            doc.metadata["source_file"] = os.path.basename(file_path)
            doc.metadata["source_path"] = file_path
            doc.metadata["file_md5"] = md5_hex

        chunk_ids = self._batch_add_documents(split_documents, user_id=user_id)
        self._save_file_md5(md5_hex, user_id=user_id)
        logger.info(
            f"[鍔犺浇鐭ヨ瘑搴揮]鍔犺浇鎴愬姛: {file_path}, chunks={len(chunk_ids)}, user_id={user_id}"
        )

        return {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "md5": md5_hex,
            "skipped": False,
            "reason": "",
            "chunk_count": len(chunk_ids),
            "chunk_ids": chunk_ids,
        }

    def load_document(self):
        allowed_files_path = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            try:
                self.add_file(path)
            except Exception as e:
                logger.error(f"[鍔犺浇鐭ヨ瘑搴揮]鍔犺浇澶辫触: {path}, {str(e)}", exc_info=True)

    def get_all_documents_with_ids(self):
        return self.list_chunks(limit=self._count_where(), offset=0)["chunks"]

    def list_chunks(self, limit: int = 20, offset: int = 0, user_id: str | None = None) -> dict:
        start = max(offset, 0)
        page_limit = max(limit, 0)
        where = self._build_where(user_id=user_id)
        total = self._count_where(where)
        result = self.vector_store.get(
            where=where,
            limit=page_limit,
            offset=start,
            include=["metadatas", "documents"],
        )
        chunks = [
            {
                "doc_id": item["doc_id"],
                "content": item["content"],
                "metadata": item["metadata"],
            }
            for item in self._result_to_chunks(result)
        ]
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "chunks": chunks,
        }

    def search_chunks(self, query: str, k: int = 5, user_id: str | None = None) -> list[dict]:
        if user_id:
            return self.search_user_knowledge(user_id, query, k)

        docs = self.vector_store.similarity_search(query, k=k)
        return [
            {
                "doc_id": (doc.metadata or {}).get("doc_id", ""),
                "content": doc.page_content,
                "metadata": doc.metadata or {},
            }
            for doc in docs
        ]

    def retrieve_documents(self, query: str, k: int = 10, user_id: str | None = None) -> list[Document]:
        if user_id:
            return self.retrieve_user_documents(user_id, query, k)
        return self.vector_store.similarity_search(query, k=k, filter={"user_id": "__shared__"})

    def retrieve_user_documents(self, user_id: str, query: str, k: int = 10) -> list[Document]:
        def search_shared():
            return self.vector_store.similarity_search(query, k=k, filter={"user_id": "__shared__"})

        def search_user():
            return self.vector_store.similarity_search(query, k=k, filter={"user_id": user_id})

        with ThreadPoolExecutor(max_workers=2) as pool:
            shared_docs = pool.submit(search_shared)
            user_docs = pool.submit(search_user)
            docs = shared_docs.result() + user_docs.result()

        seen = set()
        merged = []
        for doc in docs:
            identity = get_document_identity(doc)
            if identity in seen:
                continue
            seen.add(identity)
            merged.append(doc)
        return merged[:k]

    def search_user_knowledge(self, user_id: str, query: str, k: int = 5) -> list[dict]:
        return [
            {
                "doc_id": (doc.metadata or {}).get("doc_id", ""),
                "content": doc.page_content,
                "metadata": doc.metadata or {},
            }
            for doc in self.retrieve_user_documents(user_id, query, k)
        ][:k]

    def list_user_chunks(self, user_id: str, limit: int = 100, offset: int = 0) -> dict:
        return self.list_chunks(limit=limit, offset=offset, user_id=user_id)

    def get_chunk(self, doc_id: str, user_id: str | None = None) -> dict | None:
        where = self._build_where(user_id=user_id, doc_id=doc_id)
        result = self.vector_store.get(
            where=where,
            limit=1,
            offset=0,
            include=["metadatas", "documents"],
        )
        chunks = self._result_to_chunks(result)
        return chunks[0] if chunks else None

    def delete_document(self, doc_id: str, user_id: str | None = None) -> bool:
        chunk = self.get_chunk(doc_id, user_id=user_id)
        if not chunk:
            logger.info(f"[鍚戦噺搴?]鏈壘鍒板緟鍒犻櫎 chunk: {doc_id}, user_id={user_id or 'any'}")
            return False

        self.vector_store.delete(ids=[chunk["vector_id"]])
        logger.info(f"[鍚戦噺搴?]宸插垹闄? {doc_id} (user_id={user_id or 'any'})")
        return True

    def clear_collection(self):
        all_ids = self.vector_store.get(include=[])["ids"]
        if all_ids:
            self.vector_store.delete(ids=list(all_ids))
        with self._md5_store_lock:
            self._write_md5_store(self._empty_md5_store())
        logger.info("[鍚戦噺搴?]宸叉竻绌烘枃妗ｅ拰 MD5 璁板綍")

    def _rebuild_md5_store(self):
        allowed_files = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )
        payload = self._empty_md5_store()
        for path in allowed_files:
            md5_hex = get_file_md5_hex(path)
            if md5_hex:
                payload["records"].setdefault(self._md5_scope("__shared__"), []).append(md5_hex)
        with self._md5_store_lock:
            self._write_md5_store(payload)
