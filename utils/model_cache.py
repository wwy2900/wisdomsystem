"""Helpers for writable model/cache directories used by PDF parsing."""

from __future__ import annotations

import os
import threading

from utils.logger_handler import logger
from utils.path_tool import get_abs_path


_CACHE_LOG_LOCK = threading.Lock()
_CACHE_LOGGED = False


def ensure_docling_cache_dirs() -> dict[str, str]:
    """Point HuggingFace/Docling caches to a writable project-local directory by default."""
    base_dir = os.getenv("DOC_MODEL_CACHE_DIR", "").strip() or get_abs_path("data/model_cache")
    hf_home = os.getenv("HF_HOME", "").strip() or os.path.join(base_dir, "huggingface")
    hub_cache = os.getenv("HUGGINGFACE_HUB_CACHE", "").strip() or os.path.join(hf_home, "hub")
    transformers_cache = os.getenv("TRANSFORMERS_CACHE", "").strip() or os.path.join(base_dir, "transformers")

    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(hf_home, exist_ok=True)
    os.makedirs(hub_cache, exist_ok=True)
    os.makedirs(transformers_cache, exist_ok=True)

    os.environ["DOC_MODEL_CACHE_DIR"] = base_dir
    os.environ["HF_HOME"] = hf_home
    os.environ["HUGGINGFACE_HUB_CACHE"] = hub_cache
    os.environ["TRANSFORMERS_CACHE"] = transformers_cache

    global _CACHE_LOGGED
    if not _CACHE_LOGGED:
        with _CACHE_LOG_LOCK:
            if not _CACHE_LOGGED:
                logger.info(
                    "[Docling] writable cache configured: base=%s hub=%s transformers=%s",
                    base_dir,
                    hub_cache,
                    transformers_cache,
                )
                _CACHE_LOGGED = True

    return {
        "base_dir": base_dir,
        "hf_home": hf_home,
        "hub_cache": hub_cache,
        "transformers_cache": transformers_cache,
    }
