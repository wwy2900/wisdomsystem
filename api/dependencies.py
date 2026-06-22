"""FastAPI dependencies for API key auth and browser session auth."""
import os
from typing import Any, TYPE_CHECKING

from fastapi import Cookie, Depends, Header, HTTPException, Request, status

from services.auth_service import AuthService
from utils.logger_handler import logger

if TYPE_CHECKING:
    from services.chat_service import ChatService
    from services.knowledge_service import KnowledgeService


def verify_api_key(x_api_key: str = Header(None, alias="X-API-Key")):
    expected_key = os.getenv("FASTAPI_API_KEY", "")
    if not expected_key:
        logger.warning("[API] FASTAPI_API_KEY not configured; legacy API key protection disabled")
        return
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


def get_chat_service(request: Request):
    return request.app.state.chat_service


def get_knowledge_service(request: Request):
    return request.app.state.knowledge_service


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_current_user(
    auth_service: AuthService = Depends(get_auth_service),
    auth_session_id: str | None = Cookie(
        default=None,
        alias=os.getenv("AUTH_SESSION_COOKIE_NAME", "wisdomsystem_session"),
    ),
) -> dict[str, Any]:
    user = auth_service.get_current_user(auth_session_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


def require_admin(current_user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user
