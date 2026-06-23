"""Admin-only user management routes."""
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_auth_service, require_admin
from api.schemas import CreateUserRequest, UserListResponse, UserSummary
from services.auth_service import AuthService, UserConflictError, UserValidationError


router = APIRouter(prefix="/api/v1/admin/users", tags=["admin"])


@router.get("", response_model=UserListResponse)
def list_users(
    current_user: dict = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    del current_user
    return UserListResponse(users=[UserSummary(**item) for item in auth_service.list_users()])


@router.post("", response_model=UserSummary)
def create_user(
    req: CreateUserRequest,
    current_user: dict = Depends(require_admin),
    auth_service: AuthService = Depends(get_auth_service),
):
    del current_user
    try:
        return UserSummary(**auth_service.create_user(req.username, req.password, req.display_name, role=req.role))
    except UserConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except UserValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
