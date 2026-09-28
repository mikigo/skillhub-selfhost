import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.service import register_user, login
from skillhub_selfhost.config import Config


def make_zip(skill_name: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{skill_name}/SKILL.md", "# Test")
    return buf.getvalue()


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def auth_client(app):
    config = Config()
    await register_user("testuser", "pass123", status="active")
    tokens = await login("testuser", "pass123", config.secret_key)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {tokens['access_token']}"
        yield c


@pytest.mark.asyncio
async def test_upload_skill(auth_client):
    tar = make_zip("router-skill")
    files = {"file": ("skill.zip", tar, "application/zip")}
    data = {
        "display_name": "Router Skill",
        "description": "test",
        "tags": '["test"]',
        "version": "1.0.0",
    }
    resp = await auth_client.post("/api/skills/", files=files, data=data)
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_get_skill_list(client, auth_client):
    tar = make_zip("list-r-skill-" + str(hash("test")))
    files = {"file": ("skill.zip", tar, "application/zip")}
    data = {"display_name": "List", "description": "d", "tags": '["x"]', "version": "1.0.0"}
    await auth_client.post("/api/skills/", files=files, data=data)
    resp = await client.get("/api/skills/")
    assert resp.status_code == 200
    j = resp.json()
    assert "items" in j


@pytest.mark.asyncio
async def test_download_increments_count(client, auth_client):
    name = "count-skill-" + str(hash("count"))
    tar = make_zip(name)
    files = {"file": ("skill.zip", tar, "application/zip")}
    data = {"display_name": "C", "description": "d", "tags": '[]', "version": "1.0.0"}
    await auth_client.post("/api/skills/", files=files, data=data)
    resp = await client.get(f"/api/skills/{name}/download")
    assert resp.status_code == 200
    detail = await client.get(f"/api/skills/{name}")
    assert detail.json()["download_count"] == 1