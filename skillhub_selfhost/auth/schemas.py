# skillhub_selfhost/auth/schemas.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from uuid import UUID

class RegisterRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
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