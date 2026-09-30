import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.service import register_user


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register(client):
    resp = await client.post("/api/auth/register", json={"username": "newuser", "password": "pass123"})
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_register_duplicate(client):
    await register_user("dup", "pass1")
    resp = await client.post("/api/auth/register", json={"username": "dup", "password": "pass2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["has space", "has/slash", "%2e", "中文", "-leading", "a@b"])
async def test_register_rejects_usernames_unsafe_in_a_url_path(client, username):
    """用户名要当 /skills/<username>/<name> 的路径段用，含分隔符或需转义的字符一律拒绝。"""
    resp = await client.post("/api/auth/register", json={"username": username, "password": "pass123"})
    assert resp.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("username", ["abc", "a1", "user.name", "user_name", "user-name", "A9"])
async def test_register_accepts_safe_usernames(client, username):
    resp = await client.post("/api/auth/register", json={"username": username, "password": "pass123"})
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_login_success(client):
    await register_user("loginuser", "pass123", status="active")
    resp = await client.post("/api/auth/login", json={"username": "loginuser", "password": "pass123"})
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_login_pending(client):
    await register_user("pend", "pass123", status="pending")
    resp = await client.post("/api/auth/login", json={"username": "pend", "password": "pass123"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_me_unauthorized(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authorized(client):
    user = await register_user("meuser", "pass123", status="active")
    tokens_resp = await client.post("/api/auth/login", json={"username": "meuser", "password": "pass123"})
    token = tokens_resp.json()["access_token"]
    resp = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "meuser"


@pytest.mark.asyncio
async def test_refresh(client):
    await register_user("refuser", "pass123", status="active")
    tokens = await client.post("/api/auth/login", json={"username": "refuser", "password": "pass123"})
    refresh = tokens.json()["refresh_token"]
    resp = await client.post("/api/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    new_tokens = resp.json()
    assert new_tokens["access_token"] != tokens.json()["access_token"]