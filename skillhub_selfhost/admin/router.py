from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from skillhub_selfhost.auth.dependencies import require_admin
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.auth.service import register_user
from skillhub_selfhost.admin.schemas import CreateUserRequest

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users/")
async def list_users(
    status_filter: Optional[str] = Query(None, alias="status"),
    is_admin: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    _: User = Depends(require_admin),
):
    qs = User.all()
    if status_filter:
        qs = qs.filter(status=status_filter)
    if is_admin is not None:
        qs = qs.filter(is_admin=is_admin)
    total = await qs.count()
    users = await qs.offset((page - 1) * size).limit(size).all()
    items = [{"id": str(u.id), "username": u.username, "status": u.status, "is_admin": u.is_admin, "created_at": u.created_at} for u in users]
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/users/", status_code=201)
async def create_user(body: CreateUserRequest, _: User = Depends(require_admin)):
    try:
        user = await register_user(body.username, body.password, status="active")
        return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.patch("/users/{user_id}/approve")
async def approve_user(user_id: str, _: User = Depends(require_admin)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "active"
    await user.save()
    return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}


@router.patch("/users/{user_id}/disable")
async def disable_user(user_id: str, _: User = Depends(require_admin)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.is_admin:
        raise HTTPException(status_code=403, detail="不能禁用管理员账号")
    user.status = "disabled"
    await user.save()
    return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}


@router.patch("/users/{user_id}/enable")
async def enable_user(user_id: str, _: User = Depends(require_admin)):
    user = await User.filter(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    user.status = "active"
    await user.save()
    return {"id": str(user.id), "username": user.username, "status": user.status, "is_admin": user.is_admin, "created_at": user.created_at}