from langchain_chroma import Chroma
from langchain_core.documents import Document
from utils.config_handler import chroma_conf

from model.factory import embed_model

from rag.question_splitter import QuestionBasedSplitter
from utils.path_tool import get_abs_path
from utils.file_handler import pdf_loader, txt_loader, listdir_with_allowed_type, get_file_md5_hex
from utils.logger_handler import logger

import os


class VectorStoreService:
    def __init__(self):
        self.vector_store = Chroma(
            collection_name=chroma_conf["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_conf["persist_directory"],
        )

        # 使用按问题切分器
        self.spliter = QuestionBasedSplitter()

        self.batch_size = 10

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": 10})

    def _get_md5_path(self) -> str:
        return get_abs_path(chroma_conf["md5_hex_store"])

    def _ensure_md5_store(self):
        md5_path = self._get_md5_path()
        md5_dir = os.path.dirname(md5_path)
        if md5_dir:
            os.makedirs(md5_dir, exist_ok=True)
        if not os.path.exists(md5_path):
            open(md5_path, "w", encoding="utf-8").close()

    def _check_file_exists(self, md5_for_check: str) -> bool:
        self._ensure_md5_store()
        with open(self._get_md5_path(), "r", encoding="utf-8") as f:
            return any(line.strip() == md5_for_check for line in f)

    def _save_file_md5(self, md5_for_save: str):
        self._ensure_md5_store()
        with open(self._get_md5_path(), "a", encoding="utf-8") as f:
            f.write(md5_for_save + "\n")

    def _get_file_documents(self, read_path: str) -> list[Document]:
        lower_path = read_path.lower()
        if lower_path.endswith(".txt"):
            return txt_loader(read_path)

        if lower_path.endswith(".pdf"):
            return pdf_loader(read_path)

        return []

    def _batch_add_documents(self, documents: list[Document]) -> list[str]:
        """分批添加文档，每批最多10个，为每个文档设置独立的 doc_id（序号格式）"""
        added_doc_ids = []
        for i in range(0, len(documents), self.batch_size):
            batch = documents[i:i+self.batch_size]
            existing_count = len(self.vector_store.get()['ids'])
            for idx, doc in enumerate(batch):
                doc_id = f"chunk_{existing_count + idx + 1:04d}"
                if not doc.metadata:
                    doc.metadata = {}
                doc.metadata["doc_id"] = doc_id
                added_doc_ids.append(doc_id)
            self.vector_store.add_documents(batch)
        return added_doc_ids

    def add_file(self, file_path: str) -> dict:
        """加载单个 txt/pdf 文件并写入向量库，使用 MD5 去重。"""
        allowed_types = tuple(f".{t.lstrip('.')}" for t in chroma_conf["allow_knowledge_file_type"])
        if not file_path.lower().endswith(allowed_types):
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": None,
                "skipped": True,
                "reason": "unsupported_file_type",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        md5_hex = get_file_md5_hex(file_path)
        if not md5_hex:
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": None,
                "skipped": True,
                "reason": "md5_failed",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        if self._check_file_exists(md5_hex):
            logger.info(f"[加载知识库]{file_path}内容已经存在知识库内，跳过")
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": md5_hex,
                "skipped": True,
                "reason": "duplicate_md5",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        documents = self._get_file_documents(file_path)
        if not documents:
            logger.warning(f"[加载知识库]{file_path}内没有有效文本内容，跳过")
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": md5_hex,
                "skipped": True,
                "reason": "empty_document",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        split_documents = self.spliter.split_documents(documents)
        if not split_documents:
            logger.warning(f"[加载知识库]{file_path}分片后没有有效文本内容，跳过")
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "md5": md5_hex,
                "skipped": True,
                "reason": "empty_chunks",
                "chunk_count": 0,
                "chunk_ids": [],
            }

        for doc in split_documents:
            if not doc.metadata:
                doc.metadata = {}
            doc.metadata["source_file"] = os.path.basename(file_path)
            doc.metadata["source_path"] = file_path
            doc.metadata["file_md5"] = md5_hex

        chunk_ids = self._batch_add_documents(split_documents)
        self._save_file_md5(md5_hex)
        logger.info(f"[加载知识库]{file_path} 内容加载成功，共 {len(chunk_ids)} 个 chunk")

        return {
            "file_path": file_path,
            "file_name": os.path.basename(file_path),
            "md5": md5_hex,
            "skipped": False,
            "reason": "",
            "chunk_count": len(chunk_ids),
            "chunk_ids": chunk_ids,
        }

    def load_document(self):
        """
        从数据文件夹内读取数据文件，转为向量存入向量库
        使用文件 MD5 做去重
        :return: None
        """

        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            try:
                self.add_file(path)
            except Exception as e:
                logger.error(f"[加载知识库]{path}加载失败：{str(e)}", exc_info=True)
                continue

    def get_all_documents_with_ids(self):
        """获取所有文档及其 doc_id"""
        docs = self.vector_store.get()
        results = []
        for i, id in enumerate(docs['ids']):
            doc = Document(
                page_content=docs['documents'][i],
                metadata=docs['metadatas'][i] if docs['metadatas'] else {}
            )
            results.append({
                "doc_id": doc.metadata.get("doc_id", id),
                "content": doc.page_content,
                "metadata": doc.metadata,
            })
        return results

    def list_chunks(self, limit: int = 20, offset: int = 0) -> dict:
        """分页获取向量库 chunk。"""
        all_docs = self.get_all_documents_with_ids()
        total = len(all_docs)
        start = max(offset, 0)
        end = start + max(limit, 0)
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "chunks": all_docs[start:end],
        }

    def search_chunks(self, query: str, k: int = 5) -> list[dict]:
        """检索知识库 chunk，用于管理端预览命中结果。"""
        docs = self.vector_store.similarity_search(query, k=k)
        results = []
        for doc in docs:
            metadata = doc.metadata or {}
            results.append({
                "doc_id": metadata.get("doc_id", ""),
                "content": doc.page_content,
                "metadata": metadata,
            })
        return results

    def delete_document(self, doc_id: str):
        """删除指定 doc_id 的向量库 chunk，不删除原始文件。"""
        self.vector_store._collection.delete(where={"doc_id": doc_id})
        logger.info(f"[向量库]已删除文档: {doc_id}")

    def clear_collection(self):
        """清空向量库，用于重建"""
        all_ids = self.vector_store.get()['ids']
        if all_ids:
            self.vector_store._collection.delete(ids=all_ids)
        # 清空 MD5 文件
        md5_path = self._get_md5_path()
        open(md5_path, "w", encoding="utf-8").close()
        logger.info("[向量库]已清空所有文档和 MD5 记录")

    def _rebuild_md5_store(self):
        """重新生成 MD5 记录文件（基于现有数据文件）"""
        md5_path = get_abs_path(chroma_conf["md5_hex_store"])
        allowed_files = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"])
        )
        with open(md5_path, "w", encoding="utf-8") as f:
            for path in allowed_files:
                f.write(get_file_md5_hex(path) + "\n")


if __name__ == '__main__':
    vs = VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")
    for r in res:
        print(f"doc_id: {r.metadata.get('doc_id')}")
        print(r.page_content)
        print("-"*20)
