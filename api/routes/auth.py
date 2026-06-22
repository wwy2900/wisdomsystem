"""Browser authentication routes."""
import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from api.dependencies import get_auth_service, get_current_user
from api.schemas import (
    AuthSessionResponse,
    CurrentUserResponse,
    LoginRequest,
    OperationStatusResponse,
)
from services.auth_service import AuthError, AuthService


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=AuthSessionResponse)
def login(
    req: LoginRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        session_id, user = auth_service.login(req.username, req.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    response.set_cookie(
        key=auth_service.cookie_name,
        value=session_id,
        httponly=True,
        secure=auth_service.cookie_secure,
        samesite=auth_service.cookie_samesite,
        max_age=auth_service.session_ttl_hours * 3600,
        path="/",
    )
    return AuthSessionResponse(user=CurrentUserResponse(**user))


@router.post("/logout", response_model=OperationStatusResponse)
def logout(
    response: Response,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    auth_session_id: str | None = Cookie(
        default=None,
        alias=os.getenv("AUTH_SESSION_COOKIE_NAME", "wisdomsystem_session"),
    ),
):
    del current_user
    auth_service.logout(auth_session_id)
    response.delete_cookie(key=auth_service.cookie_name, path="/")
    return OperationStatusResponse(ok=True, message="Logged out")


@router.get("/me", response_model=CurrentUserResponse)
def me(current_user: dict = Depends(get_current_user)):
    return CurrentUserResponse(**current_user)
