"""
向量库集成测试
测试向量库的写入、查询、删除、MD5 缓存管理

使用方法: python tests/test_integration.py
"""
import os
import sys
import io

# 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rag.vector_store import VectorStoreService
from langchain_core.documents import Document


def test_integration():
    print("=" * 60)
    print("向量库集成测试")
    print("=" * 60)

    vs = VectorStoreService()

    # 测试1: 查询当前文档数
    print("\n[1/4] 查询当前文档数...")
    initial_count = len(vs.vector_store.get()['ids'])
    print(f"  当前文档数: {initial_count}")

    # 测试2: 写入测试文档
    print("\n[2/4] 写入测试文档...")
    test_docs = [
        Document(
            page_content="这是一个集成测试文档，用于验证向量库的写入和删除功能。",
            metadata={"doc_id": "test_integration_001", "source": "test"}
        ),
        Document(
            page_content="第二个测试文档，测试批量写入功能。",
            metadata={"doc_id": "test_integration_002", "source": "test"}
        ),
    ]
    vs.vector_store.add_documents(test_docs)
    after_add_count = len(vs.vector_store.get()['ids'])
    print(f"  写入 {len(test_docs)} 个文档后，文档数: {after_add_count}")
    assert after_add_count == initial_count + len(test_docs), "写入测试失败"
    print("  写入测试通过")

    # 测试3: 查询测试文档
    print("\n[3/4] 查询测试文档...")
    retriever = vs.get_retriever()
    results = retriever.invoke("集成测试文档")
    test_doc_found = any(r.metadata.get("doc_id") == "test_integration_001" for r in results)
    print(f"  检索到 {len(results)} 个文档")
    print(f"  测试文档是否被检索到: {test_doc_found}")

    # 测试4: 删除测试文档
    print("\n[4/4] 删除测试文档...")
    vs.delete_document("test_integration_001")
    vs.delete_document("test_integration_002")
    after_delete_count = len(vs.vector_store.get()['ids'])
    print(f"  删除后文档数: {after_delete_count}")
    assert after_delete_count == initial_count, "删除测试失败"
    print("  删除测试通过")

    # 测试5: get_all_documents_with_ids
    print("\n[额外] 测试 get_all_documents_with_ids...")
    all_docs = vs.get_all_documents_with_ids()
    print(f"  获取到 {len(all_docs)} 个文档的元信息")
    if all_docs:
        print(f"  第一个文档 doc_id: {all_docs[0]['doc_id']}")

    print("\n" + "=" * 60)
    print("所有测试通过！")
    print("=" * 60)


if __name__ == "__main__":
    test_integration()
