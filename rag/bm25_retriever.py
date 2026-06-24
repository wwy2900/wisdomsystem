import os
import threading
from functools import lru_cache

import jieba
from rank_bm25 import BM25Okapi

from rag.document_parsers import DocumentParserFactory
from utils.knowledge_sources import iter_knowledge_source_files
from utils.logger_handler import logger


class BM25Retriever:
    def __init__(self, upload_dir: str = "data/knowledge_uploads"):
        self.upload_dir = upload_dir
        self.corpus = []
        self.documents = []
        self.bm25 = None
        self._scope_indexes: dict[str, dict] = {}
        self._scope_status: dict[str, str] = {}
        self._scope_errors: dict[str, str] = {}
        self._scope_threads: dict[str, threading.Thread] = {}
        self._scope_lock = threading.Lock()

    @staticmethod
    def _normalize_scope(user_id: str | None = None) -> str:
        return (user_id or "__shared__").strip() or "__shared__"

    def _set_active_index(self, index: dict):
        self.corpus = index["corpus"]
        self.documents = index["documents"]
        self.bm25 = index["bm25"]

    def _build_scope_index(self, user_id: str | None = None) -> dict:
        scope = self._normalize_scope(user_id)
        corpus = []
        documents = []

        for filepath, source_user_id in iter_knowledge_source_files(upload_dir=self.upload_dir):
            if source_user_id != "__shared__" and source_user_id != scope:
                continue

            try:
                docs = DocumentParserFactory.parse(filepath)
            except Exception as error:
                logger.error(f"[BM25Retriever] failed to parse {filepath}: {error}", exc_info=True)
                continue

            for doc in docs:
                doc.metadata = dict(doc.metadata or {})
                doc.metadata["user_id"] = source_user_id
                doc.metadata.setdefault("source_path", filepath)
                doc.metadata.setdefault("source_file", os.path.basename(filepath))
                documents.append(doc)
                corpus.append(doc.page_content)

        bm25 = None
        if corpus:
            tokenized_corpus = [list(self._tokenize(doc)) for doc in corpus]
            bm25 = BM25Okapi(tokenized_corpus)

        index = {
            "corpus": corpus,
            "documents": documents,
            "bm25": bm25,
        }
        self._scope_indexes[scope] = index
        return index

    def _build_scope_index_safe(self, scope: str):
        try:
            user_id = None if scope == "__shared__" else scope
            index = self._build_scope_index(user_id=user_id)
            with self._scope_lock:
                self._scope_status[scope] = "ready"
                self._scope_errors.pop(scope, None)
                self._scope_threads.pop(scope, None)
            logger.info("[BM25Retriever] scope %s ready with %s documents", scope, len(index["documents"]))
        except Exception as error:
            with self._scope_lock:
                self._scope_status[scope] = "failed"
                self._scope_errors[scope] = str(error)
                self._scope_threads.pop(scope, None)
            logger.error("[BM25Retriever] scope %s build failed: %s", scope, error, exc_info=True)

    def prepare_scope(self, user_id: str | None = None, blocking: bool = False, timeout: float | None = None) -> bool:
        scope = self._normalize_scope(user_id)
        thread = None

        with self._scope_lock:
            if scope in self._scope_indexes:
                self._set_active_index(self._scope_indexes[scope])
                return True

            status = self._scope_status.get(scope)
            if status != "building":
                self._scope_status[scope] = "building"
                thread = threading.Thread(target=self._build_scope_index_safe, args=(scope,), daemon=True)
                self._scope_threads[scope] = thread
                thread.start()
            else:
                thread = self._scope_threads.get(scope)

        if blocking and thread is not None:
            thread.join(timeout=timeout)

        index = self._scope_indexes.get(scope)
        if index is not None:
            self._set_active_index(index)
            return True
        return False

    def get_scope_status(self, user_id: str | None = None) -> str:
        scope = self._normalize_scope(user_id)
        if scope in self._scope_indexes:
            return "ready"
        return self._scope_status.get(scope, "idle")

    def preload_shared_scope(self):
        self.prepare_scope(user_id=None, blocking=False)

    def reload(self):
        self._scope_indexes.clear()
        self._scope_status.clear()
        self._scope_errors.clear()
        self._scope_threads.clear()
        self.corpus = []
        self.documents = []
        self.bm25 = None

    @lru_cache(maxsize=1000)
    def _tokenize(self, text: str) -> tuple:
        return tuple(jieba.lcut(text))

    def retrieve(self, query: str, k: int = 10, user_id: str | None = None) -> list:
        if not self.prepare_scope(user_id=user_id, blocking=False):
            return []

        scope = self._normalize_scope(user_id)
        index = self._scope_indexes.get(scope)
        if not index or not index["bm25"]:
            return []

        tokenized_query = list(self._tokenize(query))
        scores = index["bm25"].get_scores(tokenized_query)
        top_n_indices = scores.argsort()[-k:][::-1]

        results = []
        for idx in top_n_indices:
            if scores[idx] > 0:
                doc = index["documents"][idx]
                doc.metadata["score"] = scores[idx]
                results.append(doc)

        return results
