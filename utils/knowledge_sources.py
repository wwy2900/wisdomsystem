import os
from collections.abc import Iterable
from urllib.parse import unquote

from utils.config_handler import chroma_conf
from utils.path_tool import get_abs_path


def _resolve_path(path: str) -> str:
    return path if os.path.isabs(path) else get_abs_path(path)


def iter_knowledge_source_files(
    upload_dir: str = "data/knowledge_uploads",
    data_path: str | None = None,
    allowed_types: tuple[str, ...] | None = None,
) -> Iterable[tuple[str, str]]:
    source_data_path = _resolve_path(data_path or chroma_conf["data_path"])
    source_upload_dir = _resolve_path(upload_dir)
    normalized_allowed_types = tuple(
        f".{ext.lstrip('.').lower()}" for ext in (allowed_types or tuple(chroma_conf["allow_knowledge_file_type"]))
    )

    seen = set()
    if os.path.isdir(source_data_path):
        for filename in os.listdir(source_data_path):
            if not filename.lower().endswith(normalized_allowed_types):
                continue
            path = os.path.join(source_data_path, filename)
            abs_path = os.path.abspath(path)
            if abs_path in seen:
                continue
            seen.add(abs_path)
            yield path, "__shared__"

    if not os.path.isdir(source_upload_dir):
        return

    for current_dir, _, files in os.walk(source_upload_dir):
        rel_dir = os.path.relpath(current_dir, source_upload_dir)
        user_id = "__shared__" if rel_dir == "." else unquote(rel_dir.split(os.sep, 1)[0])
        for filename in files:
            if not filename.lower().endswith(normalized_allowed_types):
                continue
            path = os.path.join(current_dir, filename)
            abs_path = os.path.abspath(path)
            if abs_path in seen:
                continue
            seen.add(abs_path)
            yield path, user_id
