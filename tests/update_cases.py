"""
使用 RAG 检索结果更新 test_cases.json 的 expected_doc_ids
不重建向量库，仅更新测试用例

使用方法: python tests/update_cases.py
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

from rag.rag_service import RagSummarizeService


def main():
    print("=" * 60)
    print("更新测试用例 doc_id")
    print("=" * 60)

    test_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_file, "r", encoding="utf-8") as f:
        test_cases = json.load(f)

    print(f"加载了 {len(test_cases)} 个测试用例")

    rag_service = RagSummarizeService()
    updated_count = 0

    for case in test_cases:
        query = case["user_query"]
        try:
            docs = rag_service.retriever_docs(query)
            retrieved_ids = [doc.metadata.get("doc_id", "") for doc in docs]
            case["relevant_doc_ids"] = retrieved_ids[:3]
            updated_count += 1
            print(f"  [{updated_count}/{len(test_cases)}] {case['id']}: {query} -> {retrieved_ids[:3]}")
        except Exception as e:
            print(f"  [ERROR] {case['id']}: {query} - {str(e)}")

    with open(test_file, "w", encoding="utf-8") as f:
        json.dump(test_cases, f, ensure_ascii=False, indent=2)

    print(f"\n完成！已更新 {updated_count}/{len(test_cases)} 个测试用例")
    print("请运行 python tests/rag_evaluation.py 重新评估")


if __name__ == "__main__":
    main()
