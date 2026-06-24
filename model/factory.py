from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from dotenv import load_dotenv
from langchain_community.chat_models.tongyi import BaseChatModel, ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.embeddings.dashscope import embed_with_retry
from langchain_core.embeddings import Embeddings

from utils.config_handler import rag_conf
from utils.dashscope_runtime import (
    apply_dashscope_runtime,
    get_dashscope_chat_max_retries,
    get_dashscope_embedding_max_retries,
    get_dashscope_request_timeout_seconds,
)


load_dotenv()
apply_dashscope_runtime()


class TimedDashScopeEmbeddings(DashScopeEmbeddings):
    request_timeout: int = 20

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = embed_with_retry(
            self,
            input=texts,
            text_type="document",
            model=self.model,
            request_timeout=self.request_timeout,
        )
        return [item["embedding"] for item in embeddings]

    def embed_query(self, text: str) -> list[float]:
        embedding = embed_with_retry(
            self,
            input=text,
            text_type="query",
            model=self.model,
            request_timeout=self.request_timeout,
        )[0]["embedding"]
        return embedding


class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        pass


class ChatModelFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return build_chat_model(rag_conf["chat_model_name"])


class EmbeddingsFactory(BaseModelFactory):
    def generator(self) -> Optional[Embeddings | BaseChatModel]:
        return build_embedding_model(rag_conf["embedding_model_name"])


def build_chat_model(model_name: str, **extra_model_kwargs) -> ChatTongyi:
    timeout_seconds = get_dashscope_request_timeout_seconds()
    model_kwargs = {"request_timeout": timeout_seconds, **extra_model_kwargs}
    return ChatTongyi(
        model=model_name,
        model_kwargs=model_kwargs,
        max_retries=get_dashscope_chat_max_retries(),
    )


def build_embedding_model(model_name: str) -> TimedDashScopeEmbeddings:
    timeout_seconds = get_dashscope_request_timeout_seconds()
    return TimedDashScopeEmbeddings(
        model=model_name,
        request_timeout=timeout_seconds,
        max_retries=get_dashscope_embedding_max_retries(),
    )


chat_model = ChatModelFactory().generator()
embed_model = EmbeddingsFactory().generator()
