from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from rag.vector_store import VectorStoreService
from rag.query_rewriter import QueryRewriter
from rag.semantic_checker import SemanticChecker
from rag.bm25_retriever import BM25Retriever
from rag.rrf_fusion import rrf_fusion
from rag.reranker import Reranker
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import chat_model


# 单例模式：避免重复初始化重型组件
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

        self.vector_store = VectorStoreService()
        self.vector_retriever = self.vector_store.get_retriever()

        self.query_rewriter = QueryRewriter()
        self.semantic_checker = SemanticChecker()
        self.bm25_retriever = BM25Retriever()
        self.reranker = Reranker()

        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = chat_model
        self.chain = self._init_chain()
        self._initialized = True

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def _hybrid_retrieval_single(self, query: str) -> list[Document]:
        """单个Query的混合召回"""
        vector_docs = self.vector_retriever.invoke(query)
        bm25_docs = self.bm25_retriever.retrieve(query)
        return rrf_fusion(vector_docs, bm25_docs)

    def _hybrid_retrieval_multi(self, queries: list) -> list[Document]:
        """多路Query召回：每个Query各自召回，然后融合所有结果"""
        all_docs = []
        
        for query_info in queries:
            query_text = query_info["text"]
            docs = self._hybrid_retrieval_single(query_text)
            all_docs.extend(docs)
        
        if not all_docs:
            return []
        
        return rrf_fusion(all_docs, [], k=60, top_n=20)

    def retriever_docs(self, query: str) -> list[Document]:
        """完整的检索流程：多路改写 → 多路召回 → Rerank精排"""
        # 1. 多路改写并过滤（相似度≥0.8）
        valid_rewrites = self.query_rewriter.rewrite_multi_with_filter(
            query, 
            num_rewrites=3, 
            threshold=0.8
        )
        
        # 2. 准备所有要召回的Query（包括原Query）
        queries_to_retrieve = [{"text": query, "similarity": 1.0}]
        queries_to_retrieve.extend(valid_rewrites)
        
        # 3. 多路召回
        fused_docs = self._hybrid_retrieval_multi(queries_to_retrieve)
        
        # 4. Rerank精排（使用原Query进行精排）
        reranked_docs = self.reranker.rerank(query, fused_docs)
        
        return reranked_docs

    def rag_summarize(self, query: str) -> str:
        context_docs = self.retriever_docs(query)

        context = ""
        counter = 0
        for doc in context_docs:
            counter += 1
            context += f"【参考资料{counter}】: {doc.page_content}\n"

        return self.chain.invoke({
            "input": query,
            "context": context,
        })


if __name__ == '__main__':
    rag = RagSummarizeService()
    print(rag.rag_summarize("小户型适合哪些扫地机器人"))