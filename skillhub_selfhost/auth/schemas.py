# skillhub_selfhost/auth/schemas.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID

# 用户名会出现在 /skills/<username>/<name> 的路径段里，必须能安全地当路径段用。
# 只约束新注册／管理员新建的账号；存量账号不动（含特殊字符的老账号详见 README 的已知限制）。
USERNAME_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*$"

class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=1, max_length=128)

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: str
    username: str
    status: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("id", mode="before")
    @classmethod
    def coerce_id_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v