import numpy as np
from langchain_core.documents import Document
from typing import List
from model.factory import embed_model

class Reranker:
    def __init__(self):
        self.embedding_model = embed_model

    def _calculate_similarity(self, query_embedding: np.ndarray, doc_embedding: np.ndarray) -> float:
        dot_product = np.dot(query_embedding, doc_embedding)
        norm1 = np.linalg.norm(query_embedding)
        norm2 = np.linalg.norm(doc_embedding)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)

    def rerank(self, query: str, documents: List[Document], top_n: int = 5) -> List[Document]:
        if not documents:
            return []

        query_embedding = np.array(self.embedding_model.embed_query(query))
        
        scored_docs = []
        for doc in documents:
            doc_embedding = np.array(self.embedding_model.embed_query(doc.page_content))
            similarity = self._calculate_similarity(query_embedding, doc_embedding)
            scored_docs.append((doc, similarity))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return [doc for doc, score in scored_docs[:top_n]]