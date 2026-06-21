"""FastAPI 依赖：API Key 鉴权 + 服务获取"""
import os
from fastapi import Header, HTTPException, Request, status
from services.chat_service import ChatService
from services.knowledge_service import KnowledgeService
from utils.logger_handler import logger


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    """校验 API Key，缺失或错误返回 401"""
    expected_key = os.getenv("FASTAPI_API_KEY", "")
    if not expected_key:
        logger.warning("[API] FASTAPI_API_KEY 未配置，API 鉴权未启用")
        return
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def get_chat_service(request: Request) -> ChatService:
    """从 app.state 获取 ChatService 实例"""
    return request.app.state.chat_service


def get_knowledge_service(request: Request) -> KnowledgeService:
    """从 app.state 获取 KnowledgeService 实例"""
    return request.app.state.knowledge_service
