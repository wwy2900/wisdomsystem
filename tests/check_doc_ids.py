"""检查向量库中的 doc_id 与测试用例的对应关系"""
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


def main():
    vs = VectorStoreService()
    docs = vs.get_all_documents_with_ids()

    print(f"向量库中的 doc_ids 总数: {len(docs)}")
    print(f"\n前 20 个 doc_ids:")
    for d in docs[:20]:
        print(f"  {d['doc_id']}")

    print(f"\n测试用例中的 relevant_doc_ids:")
    test_file = os.path.join(os.path.dirname(__file__), "test_cases.json")
    with open(test_file, "r", encoding="utf-8") as f:
        cases = json.load(f)

    all_doc_ids = {d['doc_id'] for d in docs}
    matched = 0
    missing = 0

    for case in cases:
        expected = case.get("relevant_doc_ids", [])
        case_matched = [doc_id for doc_id in expected if doc_id in all_doc_ids]
        case_missing = [doc_id for doc_id in expected if doc_id not in all_doc_ids]
        matched += len(case_matched)
        missing += len(case_missing)
        status = "OK" if not case_missing else "MISSING"
        print(f"  [{status}] {case['id']}: {case['user_query']}")
        print(f"        期望: {expected}")
        if case_missing:
            print(f"        缺失: {case_missing}")

    print(f"\n统计:")
    print(f"  匹配的 doc_id: {matched}")
    print(f"  缺失的 doc_id: {missing}")
    print(f"  覆盖率: {matched / (matched + missing) * 100:.1f}%" if (matched + missing) > 0 else "  无数据")


if __name__ == "__main__":
    main()
