import hashlib
import json

from langchain_core.documents import Document


IDENTITY_METADATA_KEYS = (
    "source_path",
    "source",
    "file_md5",
    "file_type",
    "page",
    "section_path",
    "section_title",
    "table_index",
    "content_type",
    "json_path",
    "record_index",
    "sheet_name",
    "row_index",
    "markdown_path",
)


def get_document_identity(doc: Document) -> str:
    metadata = doc.metadata or {}
    doc_id = metadata.get("doc_id")
    if doc_id:
        return f"doc_id:{doc_id}"

    identity_metadata = {
        key: metadata.get(key)
        for key in IDENTITY_METADATA_KEYS
        if metadata.get(key) not in (None, "")
    }
    content_md5 = hashlib.md5(doc.page_content.strip().encode("utf-8")).hexdigest()
    if identity_metadata:
        encoded_metadata = json.dumps(identity_metadata, ensure_ascii=False, sort_keys=True)
        return f"meta:{encoded_metadata}|content:{content_md5}"
    return f"content:{content_md5}"
