import json
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query, status
from fastapi.responses import StreamingResponse
from skillhub_selfhost.skills.service import (
    upload_skill, list_skills, search_skills, get_skill_detail,
    get_skill_readme, download_skill, delete_skill, delete_skill_version, transfer_skill
)
from skillhub_selfhost.skills.schemas import TransferRequest
from skillhub_selfhost.auth.dependencies import get_current_user, require_user
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config
import io

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.post("/", status_code=201)
async def upload(
    file: UploadFile = File(...),
    display_name: str = Form(...),
    description: str = Form(...),
    tags: str = Form("[]"),
    version: str = Form(""),
    release_notes: str | None = Form(None),
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
            tags=json.loads(tags),
            version=version,
            author=user,
            skills_dir=config.skills_dir,
            release_notes=release_notes,
        )
    except ValueError as e:
        code = 400 if "格式" in str(e) or "必须" in str(e) else 409
        raise HTTPException(status_code=code, detail=str(e))


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


@router.get("/{name}")
async def skill_detail(name: str):
    detail = await get_skill_detail(name)
    if detail is None:
        raise HTTPException(status_code=404, detail="skill 不存在")
    return detail


@router.get("/{name}/readme")
async def readme(name: str, version: str | None = Query(None)):
    config = Config()
    try:
        content = await get_skill_readme(name, version, config.skills_dir)
        return StreamingResponse(io.BytesIO(content.encode("utf-8")), media_type="text/plain")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{name}/download")
async def download(name: str, version: str | None = Query(None)):
    config = Config()
    try:
        _, filename, content = await download_skill(name, version, config.skills_dir)
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/gzip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{name}")
async def delete(name: str, user: User = Depends(require_user)):
    try:
        await delete_skill(name, user)
    except ValueError as e:
        code = 403 if "权限" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))


@router.delete("/{name}/versions/{version}")
async def delete_version(name: str, version: str, user: User = Depends(require_user)):
    try:
        await delete_skill_version(name, version, user)
    except ValueError as e:
        code = 403 if "权限" in str(e) else 404
        raise HTTPException(status_code=code, detail=str(e))


@router.patch("/{name}/transfer")
async def transfer(name: str, body: TransferRequest, user: User = Depends(require_user)):
    try:
        await transfer_skill(name, body.target_user, user)
    except ValueError as e:
        code = 403 if "权限" in str(e) else 404 if "不存在" in str(e) else 400
        raise HTTPException(status_code=code, detail=str(e))