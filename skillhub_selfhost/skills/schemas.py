# skillhub_selfhost/skills/schemas.py
from pydantic import BaseModel
from datetime import datetime


class AuthorInfo(BaseModel):
    username: str
    status: str


class SkillListItem(BaseModel):
    name: str
    display_name: str
    description: str
    author: AuthorInfo
    latest_version: str
    tags: list[str]
    download_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SkillVersionItem(BaseModel):
    version: str
    release_notes: str | None
    file_size: int
    created_at: datetime

    model_config = {"from_attributes": True}


class SkillDetailResponse(BaseModel):
    name: str
    display_name: str
    description: str
    author: AuthorInfo
    tags: list[str]
    download_count: int
    created_at: datetime
    updated_at: datetime
    versions: list[SkillVersionItem]


class PaginatedResponse(BaseModel):
    items: list
    total: int
    page: int
    size: int


class TransferRequest(BaseModel):
    target_user: str