from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type
from functools import lru_cache
import jieba


class BM25Retriever:
    def __init__(self):
        self.corpus = []
        self.documents = []
        self.bm25 = None
        self._load_corpus()

    def _load_corpus(self):
        allowed_files = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"])
        )

        for filepath in allowed_files:
            if filepath.endswith(".txt"):
                docs = txt_loader(filepath)
            elif filepath.endswith(".pdf"):
                docs = pdf_loader(filepath)
            else:
                continue

            for doc in docs:
                self.documents.append(doc)
                self.corpus.append(doc.page_content)

        if self.corpus:
            tokenized_corpus = [list(self._tokenize(doc)) for doc in self.corpus]
            self.bm25 = BM25Okapi(tokenized_corpus)

    @lru_cache(maxsize=1000)
    def _tokenize(self, text: str) -> tuple:
        """jieba 中文分词，返回 tuple 以便缓存"""
        return tuple(jieba.lcut(text))

    def retrieve(self, query: str, k: int = 10) -> list:
        if not self.bm25:
            return []

        tokenized_query = list(self._tokenize(query))
        scores = self.bm25.get_scores(tokenized_query)
        top_n_indices = scores.argsort()[-k:][::-1]

        results = []
        for idx in top_n_indices:
            if scores[idx] > 0:
                doc = self.documents[idx]
                doc.metadata["score"] = scores[idx]
                results.append(doc)

        return results
