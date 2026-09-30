import io
import zipfile
import pytest
from httpx import ASGITransport, AsyncClient
from skillhub_selfhost.main import create_app
from skillhub_selfhost.auth.service import register_user, login
from skillhub_selfhost.config import Config


# 上传者 / 详情页 URL 里的作者名
ME = "testuser"


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
    await register_user(ME, "pass123", status="active")
    tokens = await login(ME, "pass123", config.secret_key)
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
    resp = await client.get(f"/api/skills/{ME}/{name}/download")
    assert resp.status_code == 200
    detail = await client.get(f"/api/skills/{ME}/{name}")
    assert detail.json()["download_count"] == 1

# ---------------------------------------------------------------------------
# POST /api/skills/remote
# ---------------------------------------------------------------------------

from skillhub_selfhost.skills import remote
from skillhub_selfhost.skills.errors import RemoteFetchError, ValidationError

REMOTE_FM = "---\nname: Remote Linter\ndescription: from frontmatter\ntags: [python]\n---\n# body"


def patch_fetch(monkeypatch, content=REMOTE_FM, error=None):
    async def fake(ref, branch, skill_path):
        if error is not None:
            raise error
        return content
    monkeypatch.setattr(remote, "fetch_skill_md", fake)


def patch_archive(monkeypatch, error=None):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("proj-main-abc/SKILL.md", "# remote")

    async def fake(ref, branch, skill_path):
        if error is not None:
            raise error
        return buf.getvalue()
    monkeypatch.setattr(remote, "fetch_archive", fake)


REMOTE_BODY = {"gitlab_url": "https://gitlab.com/group/proj", "branch": "main", "skill_path": "agents/foo"}


@pytest.mark.asyncio
async def test_upload_remote_returns_full_detail(auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    resp = await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    assert resp.status_code == 201
    j = resp.json()
    assert j["name"] == "foo"
    assert j["source_type"] == "gitlab"
    assert j["source_branch"] == "main"
    assert j["source_path"] == "agents/foo"
    assert j["description"] == "from frontmatter"
    assert j["versions"] == []


@pytest.mark.asyncio
async def test_remote_skill_lists_with_empty_version(client, auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    j = (await client.get("/api/skills/")).json()
    item = next(i for i in j["items"] if i["name"] == "foo")
    assert item["latest_version"] == ""
    assert item["source_type"] == "gitlab"


@pytest.mark.asyncio
async def test_upload_remote_requires_auth(client, monkeypatch):
    patch_fetch(monkeypatch)
    resp = await client.post("/api/skills/remote", json=REMOTE_BODY)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_remote_bad_input_400(auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    resp = await auth_client.post("/api/skills/remote", json={**REMOTE_BODY, "branch": "bad branch"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_upload_remote_conflict_409(auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    # 同名本地 skill：换一个路径最后一段相同的 skill，先本地传一个 foo
    tar = make_zip("foo2")
    await auth_client.post("/api/skills/", files={"file": ("s.zip", tar, "application/zip")},
                           data={"display_name": "F", "description": "d", "tags": "[]", "version": "1.0.0"})
    resp = await auth_client.post("/api/skills/remote", json={**REMOTE_BODY, "skill_path": "tools/foo2"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_upload_remote_upstream_404(auth_client, monkeypatch):
    patch_fetch(monkeypatch, error=RemoteFetchError("GitLab 项目、分支或路径不存在，或为私有仓库（本功能仅支持公开仓库）", 404))
    resp = await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    assert resp.status_code == 404
    assert "公开仓库" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_remote_upstream_502(auth_client, monkeypatch):
    patch_fetch(monkeypatch, error=RemoteFetchError("无法访问 GitLab", 502))
    resp = await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_upload_remote_upstream_429_is_503(auth_client, monkeypatch):
    patch_fetch(monkeypatch, error=RemoteFetchError("GitLab 请求过于频繁", 503))
    resp = await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_remote_readme_is_live(auth_client, client, monkeypatch):
    patch_fetch(monkeypatch, content="first")
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    assert (await client.get(f"/api/skills/{ME}/foo/readme")).text == "first"

    patch_fetch(monkeypatch, content="second")
    assert (await client.get(f"/api/skills/{ME}/foo/readme")).text == "second"


@pytest.mark.asyncio
async def test_remote_readme_upstream_error_is_502(auth_client, client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    patch_fetch(monkeypatch, error=RemoteFetchError("GitLab 挂了", 502))
    resp = await client.get(f"/api/skills/{ME}/foo/readme")
    assert resp.status_code == 502


@pytest.mark.asyncio
async def test_remote_download_is_anonymous(auth_client, client, monkeypatch):
    patch_fetch(monkeypatch)
    patch_archive(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)

    resp = await client.get(f"/api/skills/{ME}/foo/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert resp.headers["content-disposition"] == 'attachment; filename="foo.zip"'
    assert zipfile.ZipFile(io.BytesIO(resp.content)).namelist() == ["foo/SKILL.md"]

    detail = await client.get(f"/api/skills/{ME}/foo")
    assert detail.json()["download_count"] == 1


@pytest.mark.asyncio
async def test_remote_download_failure_does_not_count(auth_client, client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    patch_archive(monkeypatch, error=RemoteFetchError("归档拉取失败", 502))

    resp = await client.get(f"/api/skills/{ME}/foo/download")
    assert resp.status_code == 502
    detail = await client.get(f"/api/skills/{ME}/foo")
    assert detail.json()["download_count"] == 0


@pytest.mark.asyncio
async def test_local_upload_cannot_append_to_remote_skill(auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    tar = make_zip("foo")
    resp = await auth_client.post("/api/skills/", files={"file": ("s.zip", tar, "application/zip")},
                                  data={"display_name": "F", "description": "d", "tags": "[]", "version": "2.0.0"})
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_remote_skill_has_no_version_to_delete(auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)
    resp = await auth_client.delete(f"/api/skills/{ME}/foo/versions/1.0.0")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_upload_without_display_name_or_tags(auth_client):
    """前端已经不传这两个字段了，这个请求形态必须能通（否则是 422）。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("slim-skill/SKILL.md", "---\nname: Slim Name\ntags: [a, b]\n---\n# hi")

    resp = await auth_client.post(
        "/api/skills/",
        files={"file": ("s.zip", buf.getvalue(), "application/zip")},
        data={"description": "d"},
    )
    assert resp.status_code == 201

    detail = await auth_client.get(f"/api/skills/{ME}/slim-skill")
    j = detail.json()
    assert j["display_name"] == "Slim Name"
    assert j["tags"] == ["a", "b"]
    assert j["versions"][0]["version"] == "1.0.0"


# ---------------------------------------------------------------------------
# 同名 skill 分属不同作者：靠 URL 里的 username 区分
# ---------------------------------------------------------------------------

async def _second_author_client(app, username):
    await register_user(username, "pass123", status="active")
    tokens = await login(username, "pass123", Config().secret_key)
    c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    c.headers["Authorization"] = f"Bearer {tokens['access_token']}"
    return c


@pytest.mark.asyncio
async def test_same_name_two_authors_have_separate_urls(app, client, auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    assert (await auth_client.post("/api/skills/remote", json=REMOTE_BODY)).status_code == 201

    # 另一个作者，同样的 skill 名（路径不同，指向另一个仓库目录）
    rival = await _second_author_client(app, "rival")
    try:
        resp = await rival.post("/api/skills/remote", json={**REMOTE_BODY, "skill_path": "tools/foo"})
        assert resp.status_code == 201
        assert resp.json()["author"]["username"] == "rival"
    finally:
        await rival.aclose()

    mine = await client.get(f"/api/skills/{ME}/foo")
    theirs = await client.get("/api/skills/rival/foo")
    assert mine.status_code == theirs.status_code == 200
    assert mine.json()["author"]["username"] == ME
    assert theirs.json()["author"]["username"] == "rival"
    # 各读各的配置，说明确实是两条独立记录
    assert mine.json()["source_path"] == "agents/foo"
    assert theirs.json()["source_path"] == "tools/foo"

    items = (await client.get("/api/skills/")).json()["items"]
    assert sorted(i["author"]["username"] for i in items if i["name"] == "foo") == ["rival", "testuser"]


@pytest.mark.asyncio
async def test_unknown_username_is_404(client, auth_client, monkeypatch):
    patch_fetch(monkeypatch)
    await auth_client.post("/api/skills/remote", json=REMOTE_BODY)

    assert (await client.get("/api/skills/nobody/foo")).status_code == 404
    assert (await client.get(f"/api/skills/{ME}/nope")).status_code == 404


@pytest.mark.asyncio
async def test_old_api_url_without_username_is_a_clean_404(client):
    """不带作者的老地址不能被前端的 SPA 兜底接走 —— 那会变成 200 + HTML。"""
    resp = await client.get("/api/skills/whatever")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Not Found"
