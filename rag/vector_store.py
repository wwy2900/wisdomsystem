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

    def load_document(self):
        """
        从数据文件夹内读取数据文件，转为向量存入向量库
        使用文件 MD5 做去重
        :return: None
        """

        def check_file_exists(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_conf["md5_hex_store"])):
                open(get_abs_path(chroma_conf["md5_hex_store"]), "w", encoding="utf-8").close()
                return False

            with open(get_abs_path(chroma_conf["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f.readlines():
                    line = line.strip()
                    if line == md5_for_check:
                        return True

            return False

        def save_file_md5(md5_for_check: str):
            with open(get_abs_path(chroma_conf["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path: str):
            if read_path.endswith("txt"):
                return txt_loader(read_path)

            if read_path.endswith("pdf"):
                return pdf_loader(read_path)

            return []

        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_conf["data_path"]),
            tuple(chroma_conf["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)

            if check_file_exists(md5_hex):
                logger.info(f"[加载知识库]{path}内容已经存在知识库内，跳过")
                continue

            try:
                documents: list[Document] = get_file_documents(path)

                if not documents:
                    logger.warning(f"[加载知识库]{path}内没有有效文本内容，跳过")
                    continue

                # 使用按问题切分器
                split_document: list[Document] = self.spliter.split_documents(documents)

                if not split_document:
                    logger.warning(f"[加载知识库]{path}分片后没有有效文本内容，跳过")
                    continue

                chunk_ids = self._batch_add_documents(split_document)

                save_file_md5(md5_hex)

                logger.info(f"[加载知识库]{path} 内容加载成功，共 {len(chunk_ids)} 个 chunk")
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


if __name__ == '__main__':
    vs = VectorStoreService()

    vs.load_document()

    retriever = vs.get_retriever()

    res = retriever.invoke("迷路")
    for r in res:
        print(f"doc_id: {r.metadata.get('doc_id')}")
        print(r.page_content)
        print("-"*20)