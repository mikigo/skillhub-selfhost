from __future__ import annotations

import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from skillhub_selfhost.skills.service import (
    upload_skill, upload_remote_skill, list_skills, search_skills, get_skill_detail,
    get_skill_readme, download_skill, delete_skill, delete_skill_version, transfer_skill
)
from skillhub_selfhost.skills.errors import ConflictError, RemoteFetchError, ValidationError
from skillhub_selfhost.skills.schemas import RemoteUploadRequest, TransferRequest
from skillhub_selfhost.auth.dependencies import get_current_user, require_user
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config
import io

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("/", status_code=201)
async def upload(
    file: UploadFile = File(...),
    display_name: str | None = Form(None),
    description: str = Form(...),
    tags: str | None = Form(None),
    version: str = Form(""),
    release_notes: str | None = Form(None),
    original_author: str | None = Form(None),
    source_url: str | None = Form(None),
    user: User = Depends(require_user),
):
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    config = Config()
    content = await file.read()
    try:
        await upload_skill(
            file_content=content,
            display_name=display_name,
            description=description,
            tags=json.loads(tags) if tags else None,
            version=version,
            author=user,
            skills_dir=config.skills_dir,
            release_notes=release_notes,
            original_author=original_author,
            source_url=source_url,
        )
    except ValueError as e:
        code = 400 if "格式" in str(e) or "必须" in str(e) else 409
        raise HTTPException(status_code=code, detail=str(e))


@router.post("/remote", status_code=201)
async def upload_remote(body: RemoteUploadRequest, user: User = Depends(require_user)):
    """登记一个 GitLab 仓库中的 skill：只存指针，内容实时拉取。"""
    if user.status != "active":
        raise HTTPException(status_code=403, detail="账号已被禁用")
    try:
        skill = await upload_remote_skill(body.gitlab_url, body.branch, body.skill_path, user)
    except RemoteFetchError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # 上传者就是作者，直接用 user.username，不用等 skill.author 的懒加载
    return await get_skill_detail(user.username, skill.name)


@router.get("/")
async def list_skills_route(
    q: str | None = Query(None),
    tag: list[str] = Query(None, alias="tag"),
    author: str | None = Query(None),
    sort: str = Query("downloads"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User | None = Depends(get_current_user),
):
    author_username = None
    if author == "me" and user:
        author_username = user.username
    elif author:
        author_username = author

    if q or tag or author_username:
        items, total = await search_skills(q=q, tags=tag, author_username=author_username, page=page, size=size, sort=sort)
    else:
        items, total = await list_skills(page=page, size=size, sort=sort)
    return {"items": items, "total": total, "page": page, "size": size}


@router.get("/{username}/{name}")
async def skill_detail(username: str, name: str):
    detail = await get_skill_detail(username, name)
    if detail is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return detail


@router.get("/{username}/{name}/readme")
async def readme(username: str, name: str, version: str | None = Query(None)):
    config = Config()
    try:
        content = await get_skill_readme(username, name, version, config.skills_dir)
        return StreamingResponse(io.BytesIO(content.encode("utf-8")), media_type="text/plain")
    except RemoteFetchError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{username}/{name}/download")
async def download(username: str, name: str, version: str | None = Query(None)):
    config = Config()
    try:
        _, filename, content = await download_skill(username, name, version, config.skills_dir)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except RemoteFetchError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{username}/{name}")
async def delete(username: str, name: str, user: User = Depends(require_user)):
    try:
        await delete_skill(username, name, user)
    except ValueError as e:
        code = 403 if "权限" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))


@router.delete("/{username}/{name}/versions/{version}")
async def delete_version(username: str, name: str, version: str, user: User = Depends(require_user)):
    try:
        await delete_skill_version(username, name, version, user)
    except ValueError as e:
        code = 403 if "权限" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))


@router.patch("/{username}/{name}/transfer")
async def transfer(username: str, name: str, body: TransferRequest, user: User = Depends(require_user)):
    try:
        await transfer_skill(username, name, body.target_user, user)
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        code = 403 if "权限" in str(e) else 404 if "不存在" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))