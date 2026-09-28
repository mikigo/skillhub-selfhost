# skillhub_selfhost/auth/models.py
from tortoise.models import Model
from tortoise import fields

class User(Model):
    id = fields.UUIDField(pk=True)
    username = fields.CharField(max_length=64, unique=True, index=True)
    password_hash = fields.CharField(max_length=256)
    status = fields.CharField(max_length=16, default="pending")
    is_admin = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "users"