import time

import numpy as np

from model.factory import embed_model
from utils.dashscope_runtime import get_semantic_checker_max_retries
from utils.logger_handler import logger


class SemanticChecker:
    def __init__(self):
        self.embedding_model = embed_model
        self.max_retries = get_semantic_checker_max_retries()

    def _embed_with_retry(self, text: str) -> list[float]:
        last_error = None
        for attempt in range(self.max_retries):
            try:
                return self.embedding_model.embed_query(text)
            except Exception as error:
                last_error = error
                if attempt < self.max_retries - 1:
                    wait_time = min(1 + attempt, 2)
                    logger.warning(
                        "[SemanticChecker] embedding failed (attempt %s/%s), retry in %ss: %s: %s",
                        attempt + 1,
                        self.max_retries,
                        wait_time,
                        type(error).__name__,
                        error,
                    )
                    time.sleep(wait_time)
        logger.error("[SemanticChecker] embedding failed after %s attempts: %s", self.max_retries, last_error)
        raise last_error

    def calculate_similarity(self, text1: str, text2: str) -> float:
        embedding1 = np.array(self._embed_with_retry(text1))
        embedding2 = np.array(self._embed_with_retry(text2))

        dot_product = np.dot(embedding1, embedding2)
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)
