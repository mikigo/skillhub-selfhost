from pydantic import BaseModel, Field
from datetime import datetime

from skillhub_selfhost.auth.schemas import USERNAME_PATTERN

class CreateUserRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64, pattern=USERNAME_PATTERN)
    password: str = Field(min_length=1, max_length=128)

class UserItem(BaseModel):
    id: str
    username: str
    status: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}