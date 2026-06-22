import os
import tempfile
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("DASHSCOPE_API_KEY", "test-key")

from langchain_core.documents import Document

from rag.bm25_retriever import BM25Retriever
from rag.vector_store import VectorStoreService
from services.knowledge_service import KnowledgeService
from utils.config_handler import chroma_conf


class FakeVectorBackend:
    def __init__(self):
        self.get_calls = []
        self.delete_calls = []

    def get(self, **kwargs):
        self.get_calls.append(kwargs)

        if kwargs.get("where") == {"user_id": "user-1", "doc_id": "doc-2"}:
            return {
                "ids": ["vector-2"],
                "documents": ["second chunk"],
                "metadatas": [{"doc_id": "doc-2", "user_id": "user-1"}],
            }

        if kwargs.get("include") == []:
            return {"ids": ["vector-1", "vector-2", "vector-3"]}

        return {
            "ids": ["vector-2", "vector-3"],
            "documents": ["second chunk", "third chunk"],
            "metadatas": [
                {"doc_id": "doc-2", "user_id": "user-1"},
                {"doc_id": "doc-3", "user_id": "user-1"},
            ],
        }

    def delete(self, ids=None, **kwargs):
        self.delete_calls.append({"ids": ids, **kwargs})


class RagStabilityTests(unittest.TestCase):
    def test_bm25_retriever_reload_refreshes_corpus(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first_path = os.path.join(temp_dir, "faq.md")
            second_path = os.path.join(temp_dir, "shipping.md")
            with open(first_path, "w", encoding="utf-8") as f:
                f.write("# FAQ\n支持退货\n")

            with patch.dict(
                chroma_conf,
                {"data_path": temp_dir, "allow_knowledge_file_type": ["md"]},
                clear=False,
            ):
                retriever = BM25Retriever()
                self.assertEqual(len(retriever.documents), 1)

                with open(second_path, "w", encoding="utf-8") as f:
                    f.write("# Shipping\n48小时内发货\n")

                retriever.reload()

        self.assertEqual(len(retriever.documents), 2)
        self.assertEqual(len(retriever.corpus), 2)

    def test_vector_store_chunk_id_is_stable_and_non_sequential(self):
        service = VectorStoreService.__new__(VectorStoreService)
        document = Document(
            page_content="结构化文本内容",
            metadata={
                "source_path": "D:/data/sample.pdf",
                "file_md5": "abc123",
                "page": 2,
                "section_path": "Overview",
                "content_type": "text",
            },
        )

        first_id = service._build_chunk_id(document, 0, "user-1")
        second_id = service._build_chunk_id(document, 0, "user-1")
        third_id = service._build_chunk_id(document, 1, "user-1")

        self.assertEqual(first_id, second_id)
        self.assertNotEqual(first_id, third_id)
        self.assertTrue(first_id.startswith("chunk_"))
        self.assertNotEqual(first_id, "chunk_0001")

    def test_vector_store_list_chunks_uses_paginated_queries(self):
        backend = FakeVectorBackend()
        service = VectorStoreService.__new__(VectorStoreService)
        service.vector_store = backend

        result = service.list_chunks(limit=2, offset=1, user_id="user-1")

        self.assertEqual(result["total"], 3)
        self.assertEqual([chunk["doc_id"] for chunk in result["chunks"]], ["doc-2", "doc-3"])
        self.assertEqual(backend.get_calls[0]["where"], {"user_id": "user-1"})
        self.assertEqual(backend.get_calls[0]["include"], [])
        self.assertEqual(backend.get_calls[1]["limit"], 2)
        self.assertEqual(backend.get_calls[1]["offset"], 1)
        self.assertEqual(backend.get_calls[1]["where"], {"user_id": "user-1"})

    def test_vector_store_delete_document_uses_public_get_then_delete(self):
        backend = FakeVectorBackend()
        service = VectorStoreService.__new__(VectorStoreService)
        service.vector_store = backend

        deleted = service.delete_document("doc-2", user_id="user-1")

        self.assertTrue(deleted)
        self.assertEqual(backend.delete_calls, [{"ids": ["vector-2"]}])

    def test_knowledge_service_invalidates_rag_state_after_add_document(self):
        service = KnowledgeService.__new__(KnowledgeService)
        service.vector_store = Mock()
        service.vector_store.add_file.return_value = {
            "skipped": False,
            "chunk_count": 2,
            "chunk_ids": ["chunk_a", "chunk_b"],
        }
        service._invalidate_rag_state = Mock()

        with patch.dict(chroma_conf, {"allow_knowledge_file_type": ["md"]}, clear=False):
            result = service.add_document("guide.md", user_id="user-1")

        self.assertEqual(result["chunk_count"], 2)
        service._invalidate_rag_state.assert_called_once()

    def test_knowledge_service_skips_invalidation_for_duplicate_upload(self):
        service = KnowledgeService.__new__(KnowledgeService)
        service.vector_store = Mock()
        service.vector_store.add_file.return_value = {
            "skipped": True,
            "reason": "duplicate_md5",
            "chunk_count": 0,
            "chunk_ids": [],
        }
        service._invalidate_rag_state = Mock()

        with patch.dict(chroma_conf, {"allow_knowledge_file_type": ["md"]}, clear=False):
            service.add_document("guide.md", user_id="user-1")

        service._invalidate_rag_state.assert_not_called()

    def test_knowledge_service_delete_chunk_refreshes_retrieval_state(self):
        service = KnowledgeService.__new__(KnowledgeService)
        service.vector_store = Mock()
        service.vector_store.count_chunks.return_value = 5
        service.vector_store.delete_document.return_value = True
        service._invalidate_rag_state = Mock()

        result = service.delete_chunk("doc-2", user_id="user-1")

        self.assertTrue(result["deleted"])
        self.assertEqual(result["before_total"], 5)
        self.assertEqual(result["after_total"], 4)
        service._invalidate_rag_state.assert_called_once()


if __name__ == "__main__":
    unittest.main()
