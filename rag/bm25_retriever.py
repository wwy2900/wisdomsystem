import os
from rank_bm25 import BM25Okapi
from functools import lru_cache

import jieba
from rag.document_parsers import DocumentParserFactory
from utils.knowledge_sources import iter_knowledge_source_files
from utils.logger_handler import logger


class BM25Retriever:
    def __init__(self, upload_dir: str = "data/knowledge_uploads"):
        self.upload_dir = upload_dir
        self.corpus = []
        self.documents = []
        self.bm25 = None
        self._scope_indexes = {}

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
            except Exception as e:
                logger.error(f"[BM25Retriever] failed to parse {filepath}: {str(e)}", exc_info=True)
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

    def _get_scope_index(self, user_id: str | None = None) -> dict:
        scope = self._normalize_scope(user_id)
        index = self._scope_indexes.get(scope)
        if index is None:
            index = self._build_scope_index(user_id=user_id)
        self._set_active_index(index)
        return index

    def reload(self):
        self._scope_indexes.clear()
        self.corpus = []
        self.documents = []
        self.bm25 = None

    @lru_cache(maxsize=1000)
    def _tokenize(self, text: str) -> tuple:
        """jieba 中文分词，返回 tuple 以便缓存"""
        return tuple(jieba.lcut(text))

    def retrieve(self, query: str, k: int = 10, user_id: str | None = None) -> list:
        index = self._get_scope_index(user_id=user_id)
        if not index["bm25"]:
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
