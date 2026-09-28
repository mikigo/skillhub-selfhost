import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.service import register_user, login
from skillhub_selfhost.config import Config


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def admin_client(app):
    config = Config()
    await register_user("admin", "admin123", is_admin=True, status="active")
    tokens = await login("admin", "admin123", config.secret_key)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        yield c


@pytest.fixture
async def normal_client(app):
    config = Config()
    await register_user("normal", "pass123", status="active")
    tokens = await login("normal", "pass123", config.secret_key)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        yield c


@pytest.mark.asyncio
async def test_list_users_admin(admin_client):
    resp = await admin_client.get("/api/admin/users/")
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


@pytest.mark.asyncio
async def test_list_users_normal(normal_client):
    resp = await normal_client.get("/api/admin/users/")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_approve_user(admin_client):
    user = await register_user("approveme", "pass1", status="pending")
    resp = await admin_client.patch(f"/api/admin/users/{user.id}/approve")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_disable_user(admin_client):
    user = await register_user("disableme", "pass1", status="active")
    resp = await admin_client.patch(f"/api/admin/users/{user.id}/disable")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cannot_disable_admin(admin_client):
    admins_resp = await admin_client.get("/api/admin/users/")
    admins = admins_resp.json()["items"]
    admin_id = [u["id"] for u in admins if u["username"] == "admin"][0]
    resp = await admin_client.patch(f"/api/admin/users/{admin_id}/disable")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_user(admin_client):
    resp = await admin_client.post("/api/admin/users/", json={"username": "created", "password": "pass1"})
    assert resp.status_code == 201