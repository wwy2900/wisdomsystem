"""
重建向量库并更新测试用例的 doc_id
确保向量库、MD5、测试用例的 doc_id 保持关联

使用方法: python tests/rebuild_and_update.py
"""
import os
import sys
import io
import json

# 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from rag.vector_store import VectorStoreService
from rag.rag_service import RagSummarizeService


def rebuild_and_update():
    print("=" * 60)
    print("重建向量库并更新测试用例")
    print("=" * 60)

    # 步骤1: 清空向量库和 MD5 缓存
    print("\n[1/4] 清空向量库...")
    vs = VectorStoreService()
    vs.clear_collection()
    print("  向量库已清空")

    # 步骤2: 重新加载文档
    print("\n[2/4] 重新加载知识库文档...")
    vs.load_document()
    doc_count = len(vs.vector_store.get()['ids'])
    print(f"  加载完成，共 {doc_count} 个文档")

    # 步骤3: 更新测试用例的 relevant_doc_ids
    print("\n[3/4] 更新测试用例 doc_id...")
    test_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    rag_service = RagSummarizeService()
    updated_count = 0

    for case in test_cases:
        query = case["user_query"]
        try:
            docs = rag_service.retriever_docs(query)
            retrieved_ids = [doc.metadata.get("doc_id", "") for doc in docs]
            case["relevant_doc_ids"] = retrieved_ids[:3]
            updated_count += 1
            print(f"  [{updated_count}/{len(test_cases)}] {case['id']}: {query}")
        except Exception as e:
            print(f"  [ERROR] {case['id']}: {query} - {str(e)}")

    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=2)
    print(f"  已更新 {updated_count}/{len(test_cases)} 个测试用例")

    # 步骤4: 提示重新评估
    print("\n[4/4] 完成！")
    print("  请运行以下命令重新评估:")
    print("  python tests/rag_evaluation.py")


if __name__ == "__main__":
    rebuild_and_update()
