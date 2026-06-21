import numpy as np
from langchain_core.documents import Document
from typing import List
from model.factory import embed_model


class Reranker:
    def __init__(self):
        self.embedding_model = embed_model
        # DashScope embed_documents 批量上限为 10
        self.batch_size = 10

    def _batch_embed_documents(self, texts: List[str]) -> List[List[float]]:
        """分批嵌入文档，避免超过 API 批量限制"""
        all_embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_embeddings = self.embedding_model.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
        return all_embeddings

    def rerank(self, query: str, documents: List[Document], top_n: int = 5) -> List[Document]:
        """使用批量嵌入进行 Rerank 精排，减少 API 调用次数"""
        if not documents:
            return []

        # 分批嵌入所有文档（每批最多 10 个）
        doc_texts = [doc.page_content for doc in documents]
        doc_embeddings = np.array(self._batch_embed_documents(doc_texts))
        query_embedding = np.array(self.embedding_model.embed_query(query))

        # 向量化的相似度计算（余弦相似度）
        query_norm = np.linalg.norm(query_embedding)
        doc_norms = np.linalg.norm(doc_embeddings, axis=1)

        # 避免除零
        valid_mask = (doc_norms > 0) & (query_norm > 0)
        similarities = np.zeros(len(documents))
        if query_norm > 0:
            similarities[valid_mask] = np.dot(doc_embeddings[valid_mask], query_embedding) / (
                doc_norms[valid_mask] * query_norm
            )

        # 按相似度降序排序，取 top_n
        scored_indices = np.argsort(similarities)[::-1][:top_n]
        return [documents[i] for i in scored_indices]
