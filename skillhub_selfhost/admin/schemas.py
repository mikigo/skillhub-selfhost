from pydantic import BaseModel
from datetime import datetime

class CreateUserRequest(BaseModel):
    username: str
    password: str

class UserItem(BaseModel):
    id: str
    username: str
    status: str
    is_admin: bool
    created_at: datetime

    model_config = {"from_attributes": True}