# skillhub_selfhost/auth/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from skillhub_selfhost.auth.service import decode_token, get_user_by_id
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

security = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User | None:
    if credentials is None:
        return None
    config = Config()
    try:
        payload = decode_token(credentials.credentials, config.secret_key)
        if payload.get("type") == "refresh":
            return None
        user_id = payload.get("sub")
        user = await get_user_by_id(user_id)
        return user
    except Exception:
        return None

async def require_user(
    user: User | None = Depends(get_current_user),
) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return user

async def require_admin(
    user: User = Depends(require_user),
) -> User:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user