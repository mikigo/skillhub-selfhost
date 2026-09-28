from fastapi import APIRouter, Depends, HTTPException, status
from skillhub_selfhost.auth.schemas import RegisterRequest, LoginRequest, RefreshRequest, TokenResponse, UserResponse
from skillhub_selfhost.auth.service import register_user, login, refresh_token, get_user_by_id
from skillhub_selfhost.auth.dependencies import require_user
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=204)
async def register(body: RegisterRequest):
    try:
        await register_user(body.username, body.password)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login_route(body: LoginRequest):
    config = Config()
    try:
        return await login(body.username, body.password, config.secret_key)
    except ValueError as e:
        status_code = 403 if "审批" in str(e) or "禁用" in str(e) else 401
        raise HTTPException(status_code=status_code, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_route(body: RefreshRequest):
    config = Config()
    try:
        return await refresh_token(body.refresh_token, config.secret_key)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me", response_model=UserResponse)
async def me(user: User = Depends(require_user)):
    return user