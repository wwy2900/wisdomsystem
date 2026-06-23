"""Browser authentication routes."""
import os

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status

from api.dependencies import get_auth_service, get_current_user
from api.schemas import (
    AuthSessionResponse,
    CurrentUserResponse,
    LoginRequest,
    OperationStatusResponse,
    RegisterRequest,
)
from services.auth_service import AuthError, AuthService, UserConflictError, UserValidationError


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_session_cookie(response: Response, auth_service: AuthService, session_id: str):
    response.set_cookie(
        key=auth_service.cookie_name,
        value=session_id,
        httponly=True,
        secure=auth_service.cookie_secure,
        samesite=auth_service.cookie_samesite,
        max_age=auth_service.session_ttl_hours * 3600,
        path="/",
    )


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

    _set_session_cookie(response, auth_service, session_id)
    return AuthSessionResponse(user=CurrentUserResponse(**user))


@router.post("/register", response_model=AuthSessionResponse)
def register(
    req: RegisterRequest,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        session_id, user = auth_service.register_user(req.username, req.password, req.display_name)
    except UserConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UserValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _set_session_cookie(response, auth_service, session_id)
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
