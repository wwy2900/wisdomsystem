import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from model.factory import chat_model
from rag.bm25_retriever import BM25Retriever
from rag.query_rewriter import QueryRewriter
from rag.reranker import Reranker
from rag.rrf_fusion import rrf_fusion
from rag.semantic_checker import SemanticChecker
from rag.vector_store import VectorStoreService
from utils.logger_handler import logger
from utils.prompt_loader import load_rag_prompts


_instance = None


class RagSummarizeService:
    def __new__(cls):
        global _instance
        if _instance is None:
            _instance = super().__new__(cls)
            _instance._initialized = False
        return _instance

    def __init__(self):
        if self._initialized:
            return

        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()

        self._vector_store = None
        self._vector_retriever = None
        self._query_rewriter = None
        self._semantic_checker = None
        self._bm25_retriever = None
        self._reranker = None
        self._cache = None

        self._local_cache = {}
        self._local_cache_max = 100

        self._initialized = True

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def _get_vector_store(self):
        if self._vector_store is None:
            self._vector_store = VectorStoreService()
        return self._vector_store

    def _get_vector_retriever(self):
        if self._vector_retriever is None:
            self._vector_retriever = self._get_vector_store().get_retriever()
        return self._vector_retriever

    def _get_query_rewriter(self):
        if self._query_rewriter is None:
            self._query_rewriter = QueryRewriter()
        return self._query_rewriter

    def _get_semantic_checker(self):
        if self._semantic_checker is None:
            self._semantic_checker = SemanticChecker()
        return self._semantic_checker

    def _get_bm25_retriever(self):
        if self._bm25_retriever is None:
            self._bm25_retriever = BM25Retriever()
        return self._bm25_retriever

    def _get_reranker(self):
        if self._reranker is None:
            self._reranker = Reranker()
        return self._reranker

    def _get_cache(self):
        if self._cache is None:
            from database.redis_cache import RedisCache

            self._cache = RedisCache()
        return self._cache

    def invalidate_knowledge_state(self):
        self._vector_store = None
        self._vector_retriever = None
        self._bm25_retriever = None
        self._local_cache.clear()

        if self._cache is not None:
            try:
                self._cache.delete_cache_prefix("rag:")
            except Exception as exc:
                logger.warning(f"[RAG]缓存失效失败: {str(exc)}")

    def _local_cache_get(self, key: str):
        return self._local_cache.get(key)

    def _local_cache_set(self, key: str, value: str):
        if len(self._local_cache) >= self._local_cache_max:
            oldest_key = next(iter(self._local_cache))
            del self._local_cache[oldest_key]
        self._local_cache[key] = value

    def _hybrid_retrieval_single(self, query: str, user_id: str | None = None) -> list[Document]:
        with ThreadPoolExecutor(max_workers=2) as executor:
            vector_future = executor.submit(
                self._get_vector_store().retrieve_documents,
                query,
                10,
                user_id,
            )
            bm25_future = executor.submit(self._get_bm25_retriever().retrieve, query)
            vector_docs = vector_future.result()
            bm25_docs = bm25_future.result()
        return rrf_fusion(vector_docs, bm25_docs)

    def _hybrid_retrieval_multi(self, queries: list, user_id: str | None = None) -> list[Document]:
        all_docs = []
        if not queries:
            return []

        with ThreadPoolExecutor(max_workers=min(len(queries), 4)) as executor:
            futures = {
                executor.submit(self._hybrid_retrieval_single, item["text"], user_id): item
                for item in queries
            }
            for future in as_completed(futures):
                try:
                    docs = future.result()
                    all_docs.extend(docs)
                except Exception as exc:
                    logger.error(f"[RAG]多路召回失败: {str(exc)}")

        if not all_docs:
            return []

        return rrf_fusion(all_docs, [], k=60, top_n=20)

    def retriever_docs(self, query: str, user_id: str | None = None) -> list[Document]:
        valid_rewrites = self._get_query_rewriter().rewrite_multi_with_filter(
            query,
            num_rewrites=3,
            threshold=0.8,
        )

        queries_to_retrieve = [{"text": query, "similarity": 1.0}]
        queries_to_retrieve.extend(valid_rewrites)

        fused_docs = self._hybrid_retrieval_multi(queries_to_retrieve, user_id=user_id)
        return self._get_reranker().rerank(query, fused_docs)

    def rag_summarize(self, query: str, user_id: str | None = None) -> str:
        scope = user_id or "__shared__"
        query_hash = hashlib.md5(query.encode()).hexdigest()
        scope_hash = hashlib.md5(scope.encode()).hexdigest()
        cache_key = f"rag:{scope_hash}:{query_hash}"

        local_result = self._local_cache_get(cache_key)
        if local_result is not None:
            logger.debug(f"[RAG]命中本地缓存: {query[:30]}")
            return local_result

        try:
            redis_result = self._get_cache().get_cache(cache_key)
            if redis_result:
                logger.debug(f"[RAG]命中 Redis 缓存: {query[:30]}")
                self._local_cache_set(cache_key, redis_result)
                return redis_result
        except Exception as exc:
            logger.warning(f"[RAG]Redis 缓存读取失败: {str(exc)}")

        context_docs = self.retriever_docs(query, user_id=user_id)
        context = ""
        for index, doc in enumerate(context_docs, start=1):
            context += f"【参考资料{index}】 {doc.page_content}\n"

        result = self.chain.invoke(
            {
                "input": query,
                "context": context,
            }
        )

        self._local_cache_set(cache_key, result)
        try:
            self._get_cache().set_cache(cache_key, result, ttl_seconds=86400)
        except Exception as exc:
            logger.warning(f"[RAG]Redis 缓存写入失败: {str(exc)}")

        return result
