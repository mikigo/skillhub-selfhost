# tests/test_auth_service.py
import pytest
from skillhub_selfhost.auth.service import register_user, login, refresh_token, get_user_by_id
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

@pytest.fixture
def config():
    return Config()

@pytest.mark.asyncio
async def test_register_user(config):
    user = await register_user("alice", "password123")
    assert user.username == "alice"
    assert user.status == "pending"
    assert user.is_admin is False
    assert len(user.password_hash) > 0

@pytest.mark.asyncio
async def test_register_duplicate_username(config):
    await register_user("bob", "pass1")
    with pytest.raises(ValueError, match="用户名已存在"):
        await register_user("bob", "pass2")

@pytest.mark.asyncio
async def test_login_success(config):
    await register_user("carol", "password123", status="active")
    tokens = await login("carol", "password123", config.secret_key)
    assert "access_token" in tokens
    assert "refresh_token" in tokens

@pytest.mark.asyncio
async def test_login_pending_user(config):
    await register_user("dave", "password123", status="pending")
    with pytest.raises(ValueError, match="账号尚未通过审批"):
        await login("dave", "password123", config.secret_key)

@pytest.mark.asyncio
async def test_login_disabled_user(config):
    await register_user("eve", "password123", status="disabled")
    with pytest.raises(ValueError, match="账号已被禁用"):
        await login("eve", "password123", config.secret_key)

@pytest.mark.asyncio
async def test_login_wrong_password(config):
    await register_user("frank", "password123", status="active")
    with pytest.raises(ValueError, match="用户名或密码错误"):
        await login("frank", "wrongpass", config.secret_key)

@pytest.mark.asyncio
async def test_refresh_token(config):
    await register_user("grace", "password123", status="active")
    tokens = await login("grace", "password123", config.secret_key)
    new_tokens = await refresh_token(tokens["refresh_token"], config.secret_key)
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens
    assert new_tokens["access_token"] != tokens["access_token"]