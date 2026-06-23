import os
import tempfile
import unittest
from urllib.parse import quote
from unittest.mock import Mock, patch

os.environ.setdefault("DASHSCOPE_API_KEY", "test-key")

from langchain_core.documents import Document

from rag.bm25_retriever import BM25Retriever
from rag.rag_service import RagSummarizeService
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
        with tempfile.TemporaryDirectory() as temp_dir, tempfile.TemporaryDirectory() as upload_dir:
            first_path = os.path.join(temp_dir, "faq.md")
            second_path = os.path.join(temp_dir, "shipping.md")
            with open(first_path, "w", encoding="utf-8") as f:
                f.write("# FAQ\nSupports returns.\n")

            with patch.dict(
                chroma_conf,
                {"data_path": temp_dir, "allow_knowledge_file_type": ["md"]},
                clear=False,
            ):
                retriever = BM25Retriever(upload_dir=upload_dir)
                retriever.retrieve("returns")
                self.assertEqual(len(retriever.documents), 1)

                with open(second_path, "w", encoding="utf-8") as f:
                    f.write("# Shipping\nShips within 48 hours.\n")

                retriever.reload()
                retriever.retrieve("shipping")

        self.assertEqual(len(retriever.documents), 2)
        self.assertEqual(len(retriever.corpus), 2)

    def test_bm25_retriever_supports_user_scoped_private_knowledge(self):
        with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as upload_dir:
            with open(os.path.join(data_dir, "shared.md"), "w", encoding="utf-8") as f:
                f.write("# Shared\nShared return policy.\n")
            with open(os.path.join(upload_dir, "shared-upload.md"), "w", encoding="utf-8") as f:
                f.write("# Shared Upload\nShared shipping instructions.\n")

            user_one_dir = os.path.join(upload_dir, quote("user-1", safe=""))
            user_two_dir = os.path.join(upload_dir, quote("user-2", safe=""))
            os.makedirs(user_one_dir, exist_ok=True)
            os.makedirs(user_two_dir, exist_ok=True)

            with open(os.path.join(user_one_dir, "private-one.md"), "w", encoding="utf-8") as f:
                f.write("# Private One\nPassword reset flow for user one.\n")
            with open(os.path.join(user_two_dir, "private-two.md"), "w", encoding="utf-8") as f:
                f.write("# Private Two\nInvoice flow for user two.\n")

            with patch.dict(
                chroma_conf,
                {"data_path": data_dir, "allow_knowledge_file_type": ["md"]},
                clear=False,
            ):
                retriever = BM25Retriever(upload_dir=upload_dir)

                shared_only = retriever.retrieve("password reset")
                self.assertEqual(shared_only, [])
                self.assertEqual({doc.metadata["user_id"] for doc in retriever.documents}, {"__shared__"})

                user_one_private = retriever.retrieve("password reset", user_id="user-1")
                self.assertEqual(len(user_one_private), 1)
                self.assertEqual(user_one_private[0].metadata["user_id"], "user-1")
                self.assertEqual(
                    {doc.metadata["user_id"] for doc in retriever.documents},
                    {"__shared__", "user-1"},
                )

                user_two_private = retriever.retrieve("password reset", user_id="user-2")
                self.assertEqual(user_two_private, [])
                self.assertEqual(
                    {doc.metadata["user_id"] for doc in retriever.documents},
                    {"__shared__", "user-2"},
                )

                user_one_shared = retriever.retrieve("shipping instructions", user_id="user-1")
                self.assertEqual(len(user_one_shared), 1)
                self.assertEqual(user_one_shared[0].metadata["user_id"], "__shared__")

    def test_hybrid_retrieval_single_passes_user_id_to_vector_and_bm25(self):
        service = RagSummarizeService.__new__(RagSummarizeService)
        vector_store = Mock()
        bm25_retriever = Mock()
        vector_store.retrieve_documents.return_value = [Document(page_content="vector", metadata={"doc_id": "v1"})]
        bm25_retriever.retrieve.return_value = [Document(page_content="bm25", metadata={"doc_id": "b1"})]
        service._get_vector_store = Mock(return_value=vector_store)
        service._get_bm25_retriever = Mock(return_value=bm25_retriever)

        docs = service._hybrid_retrieval_single("how to return", user_id="user-1")

        vector_store.retrieve_documents.assert_called_once_with("how to return", 10, "user-1")
        bm25_retriever.retrieve.assert_called_once_with("how to return", 10, "user-1")
        self.assertEqual(len(docs), 2)

    def test_build_source_references_marks_knowledge_sources(self):
        documents = [
            Document(
                page_content="Replace the main brush every 6 months.",
                metadata={
                    "doc_id": "doc-1",
                    "source_file": "maintenance.md",
                    "page": 2,
                    "section_title": "Brush care",
                },
            )
        ]

        sources = RagSummarizeService.build_source_references(documents)

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0].source_type, "knowledge")
        self.assertEqual(sources[0].title, "maintenance.md")
        self.assertEqual(sources[0].tool_name, "rag_summarize")

    def test_vector_store_chunk_id_is_stable_and_non_sequential(self):
        service = VectorStoreService.__new__(VectorStoreService)
        document = Document(
            page_content="Structured document content.",
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

    def test_vector_store_load_document_uses_scoped_source_files(self):
        service = VectorStoreService.__new__(VectorStoreService)
        service.add_file = Mock()

        with patch(
            "rag.vector_store.iter_knowledge_source_files",
            return_value=[
                ("D:/data/shared.md", "__shared__"),
                ("D:/data/knowledge_uploads/user-1/private.md", "user-1"),
            ],
        ):
            service.load_document()

        self.assertEqual(
            service.add_file.call_args_list,
            [
                unittest.mock.call("D:/data/shared.md", user_id="__shared__"),
                unittest.mock.call("D:/data/knowledge_uploads/user-1/private.md", user_id="user-1"),
            ],
        )

    def test_vector_store_rebuild_md5_store_preserves_scope(self):
        service = VectorStoreService.__new__(VectorStoreService)
        captured = {}
        service._write_md5_store = lambda payload: captured.setdefault("payload", payload)

        with patch(
            "rag.vector_store.iter_knowledge_source_files",
            return_value=[
                ("D:/data/shared.md", "__shared__"),
                ("D:/data/knowledge_uploads/user-1/private.md", "user-1"),
            ],
        ), patch(
            "rag.vector_store.get_file_md5_hex",
            side_effect=["md5-shared", "md5-user-1"],
        ):
            service._rebuild_md5_store()

        self.assertEqual(
            captured["payload"]["records"],
            {
                service._md5_scope("__shared__"): ["md5-shared"],
                service._md5_scope("user-1"): ["md5-user-1"],
            },
        )

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
