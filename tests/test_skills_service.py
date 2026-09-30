# tests/test_skills_service.py
import io
import zipfile
import pytest
from skillhub_selfhost.skills.service import upload_skill
from skillhub_selfhost.skills.models import Skill, SkillVersion
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config


def make_zip(skill_name: str, has_skill_md: bool = True) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if has_skill_md:
            zf.writestr(f"{skill_name}/SKILL.md", "# Test")
    return buf.getvalue()


@pytest.fixture
def config():
    return Config()


# 用户名现在是 skill 定位的一部分（/skills/<username>/<name>），测试里统一用这个
UPLOADER = "uploader"


@pytest.fixture
async def user():
    return await User.create(username=UPLOADER, password_hash="x", status="active")


@pytest.mark.asyncio
async def test_upload_new_skill(config, user, skills_dir):
    tar_bytes = make_zip("my-linter")
    skill = await upload_skill(
        file_content=tar_bytes,
        display_name="My Linter",
        description="A linter",
        tags=["python"],
        version="1.0.0",
        author=user,
        skills_dir=skills_dir,
    )
    assert skill.name == "my-linter"
    assert skill.display_name == "My Linter"
    assert skill.author_id == user.id
    versions = await SkillVersion.filter(skill=skill).all()
    assert len(versions) == 1
    assert versions[0].version == "1.0.0"


@pytest.mark.asyncio
async def test_upload_missing_skill_md(config, user, skills_dir):
    tar_bytes = make_zip("bad-skill", has_skill_md=False)
    with pytest.raises(ValueError, match="必须包含 SKILL.md"):
        await upload_skill(tar_bytes, "Bad", "desc", [], "1.0.0", user, skills_dir)


@pytest.mark.asyncio
async def test_upload_duplicate_version(config, user, skills_dir):
    tar_bytes = make_zip("dup-skill")
    await upload_skill(tar_bytes, "Dup", "desc", [], "1.0.0", user, skills_dir)
    with pytest.raises(ValueError, match="已存在"):
        await upload_skill(tar_bytes, "Dup2", "desc2", [], "1.0.0", user, skills_dir)


@pytest.mark.asyncio
async def test_upload_auto_version(config, user, skills_dir):
    tar_bytes = make_zip("auto-skill")
    await upload_skill(tar_bytes, "Auto", "desc", [], "1.0.0", user, skills_dir)
    skill2 = await upload_skill(tar_bytes, "Auto", "desc", [], "", user, skills_dir)
    versions = await SkillVersion.filter(skill__name="auto-skill").all()
    assert len(versions) == 2
    assert versions[1].version == "1.0.1"


@pytest.mark.asyncio
async def test_list_skills(config, user):
    tar = make_zip("list-skill")
    await upload_skill(tar, "List Skill", "desc", ["python"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import list_skills
    items, total = await list_skills(page=1, size=20)
    assert total >= 1


@pytest.mark.asyncio
async def test_search_skills(config, user):
    tar = make_zip("search-skill")
    await upload_skill(tar, "Search Skill", "a unique desc word", ["go"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import search_skills
    items, total = await search_skills(q="unique desc")
    assert total >= 1


@pytest.mark.asyncio
async def test_filter_by_tag(config, user):
    tar1 = make_zip("tag-a")
    tar2 = make_zip("tag-b")
    await upload_skill(tar1, "Tag A", "desc", ["python", "linter"], "1.0.0", user, config.skills_dir)
    await upload_skill(tar2, "Tag B", "desc", ["python"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import search_skills
    items, _ = await search_skills(tags=["python", "linter"])
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_download_increments_count(config, user):
    tar = make_zip("dl-count")
    await upload_skill(tar, "DL Count", "desc", [], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import download_skill
    path, filename, content = await download_skill(UPLOADER, "dl-count")
    skill = await Skill.filter(name="dl-count").first()
    assert skill.download_count == 1


@pytest.mark.asyncio
async def test_get_skill_detail(config, user):
    tar = make_zip("detail-test")
    await upload_skill(tar, "Detail Test", "desc", ["x"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import get_skill_detail
    detail = await get_skill_detail(UPLOADER, "detail-test")
    assert detail["name"] == "detail-test"
    assert len(detail["versions"]) == 1


@pytest.mark.asyncio
async def test_get_readme(config, user):
    tar = make_zip("readme-test")
    await upload_skill(tar, "Readme Test", "desc", [], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import get_skill_readme
    content = await get_skill_readme(UPLOADER, "readme-test", skills_dir=config.skills_dir)
    assert "# Test" in content


@pytest.mark.asyncio
async def test_delete_skill(config, user):
    tar = make_zip("delete-test")
    await upload_skill(tar, "Delete", "desc", [], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import delete_skill
    await delete_skill(UPLOADER, "delete-test", user)
    s = await Skill.filter(name="delete-test").first()
    assert s is None

# ---------------------------------------------------------------------------
# 远程（GitLab）skill：patch 掉 skillhub_selfhost.skills.remote 的出站函数
# ---------------------------------------------------------------------------

from skillhub_selfhost.skills import remote
from skillhub_selfhost.skills.errors import ConflictError, ValidationError
from skillhub_selfhost.skills.models import DownloadLog
from skillhub_selfhost.skills.service import (
    download_skill, get_skill_detail, get_skill_readme, list_skills,
    upload_remote_skill,
)

FM = "---\nname: Remote Linter\ndescription: desc from frontmatter\ntags: [python, lint]\n---\n# remote"


def patch_fetch(monkeypatch, content=FM, calls=None):
    async def fake(ref, branch, skill_path):
        if calls is not None:
            calls.append((ref.project_url, branch, skill_path))
        return content
    monkeypatch.setattr(remote, "fetch_skill_md", fake)


def patch_archive(monkeypatch, entries=(("proj-main-abc/SKILL.md", "# remote"),)):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries:
            zf.writestr(name, data)

    async def fake(ref, branch, skill_path):
        return buf.getvalue()
    monkeypatch.setattr(remote, "fetch_archive", fake)


@pytest.mark.asyncio
async def test_remote_upload_creates_pointer(monkeypatch, user):
    patch_fetch(monkeypatch)
    skill = await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)

    assert skill.name == "foo"
    assert skill.source_type == "gitlab"
    assert skill.source_url == "https://gitlab.com/group/proj"
    assert skill.source_branch == "main"
    assert skill.source_path == "agents/foo"
    assert skill.display_name == "Remote Linter"
    assert skill.description == "desc from frontmatter"
    assert skill.tags == ["python", "lint"]
    assert await SkillVersion.filter(skill=skill).count() == 0


@pytest.mark.asyncio
async def test_remote_upload_display_name_falls_back(monkeypatch, user):
    patch_fetch(monkeypatch, content="no frontmatter here")
    skill = await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)
    assert skill.display_name == "foo"
    assert skill.description == ""
    assert skill.tags == []


@pytest.mark.asyncio
async def test_remote_upload_root_path_uses_project_name(monkeypatch, user):
    patch_fetch(monkeypatch)
    skill = await upload_remote_skill("https://gitlab.com/group/my-skill", "main", ".", user)
    assert skill.name == "my-skill"
    assert skill.source_path == ""


@pytest.mark.asyncio
async def test_remote_upload_bad_url_never_hits_network(monkeypatch, user):
    async def boom(*a, **kw):
        raise AssertionError("不应发起网络请求")
    monkeypatch.setattr(remote, "fetch_skill_md", boom)
    with pytest.raises(ValidationError):
        await upload_remote_skill("ftp://gitlab.com/a/b", "main", "", user)


@pytest.mark.asyncio
async def test_remote_upload_same_name_other_author_is_allowed(monkeypatch, user):
    """名称只在作者内唯一：别人已经叫 foo，我照样能有一个自己的 foo。"""
    patch_fetch(monkeypatch)
    other = await User.create(username="other", password_hash="x", status="active")
    theirs = await Skill.create(name="foo", display_name="Foo", description="", tags=[], author=other)

    mine = await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)

    assert mine.id != theirs.id
    assert mine.author_id == user.id
    assert await Skill.filter(name="foo").count() == 2


@pytest.mark.asyncio
async def test_remote_upload_conflict_with_local_skill(monkeypatch, user, config):
    await upload_skill(make_zip("foo"), "Foo", "d", [], "1.0.0", user, config.skills_dir)
    patch_fetch(monkeypatch)
    with pytest.raises(ConflictError, match="同名本地 skill"):
        await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)


@pytest.mark.asyncio
async def test_remote_upload_is_idempotent(monkeypatch, user):
    patch_fetch(monkeypatch)
    first = await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)
    patch_fetch(monkeypatch, content="---\nname: Renamed\ndescription: new\n---\n")
    second = await upload_remote_skill("https://gitlab.com/group/proj", "dev", "tools/foo", user)

    assert first.id == second.id
    assert second.display_name == "Renamed"
    assert second.description == "new"
    assert second.source_branch == "dev"
    assert second.source_path == "tools/foo"
    assert await Skill.filter(name="foo").count() == 1


@pytest.mark.asyncio
async def test_remote_readme_is_fetched_on_every_call(monkeypatch, user):
    calls = []
    patch_fetch(monkeypatch, content="v1", calls=calls)
    await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)

    patch_fetch(monkeypatch, content="v2", calls=calls)
    assert await get_skill_readme(UPLOADER, "foo") == "v2"
    assert await get_skill_readme(UPLOADER, "foo") == "v2"
    # 上传 1 次 + 每次查看各 1 次：没有任何缓存
    assert len(calls) == 3


@pytest.mark.asyncio
async def test_remote_download_repacks_and_counts(monkeypatch, user):
    patch_fetch(monkeypatch)
    patch_archive(monkeypatch, entries=[
        ("proj-main-abc/SKILL.md", "# remote"),
        ("proj-main-abc/run.sh", "echo hi"),
    ])
    await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)

    path, filename, content = await download_skill(UPLOADER, "foo")
    assert path is None
    assert filename == "foo.zip"
    names = sorted(zipfile.ZipFile(io.BytesIO(content)).namelist())
    assert names == ["foo/SKILL.md", "foo/run.sh"]

    skill = await Skill.filter(name="foo").first()
    assert skill.download_count == 1
    log = await DownloadLog.filter(skill=skill).first()
    assert log.version == ""


@pytest.mark.asyncio
async def test_remote_skill_has_no_versions_but_lists(monkeypatch, user):
    patch_fetch(monkeypatch)
    await upload_remote_skill("https://gitlab.com/group/proj", "main", "agents/foo", user)

    detail = await get_skill_detail(UPLOADER, "foo")
    assert detail["source_type"] == "gitlab"
    assert detail["versions"] == []
    assert "latest_version" not in detail

    items, total = await list_skills()
    assert total == 1
    assert items[0]["latest_version"] == ""


# ---------------------------------------------------------------------------
# 本地上传：表单不再填「展示名称」「标签」，改从 SKILL.md 取
# ---------------------------------------------------------------------------

def make_zip_md(skill_name: str, skill_md: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(f"{skill_name}/SKILL.md", skill_md)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_upload_derives_display_name_and_tags_from_frontmatter(user, skills_dir):
    tar = make_zip_md("md-skill", "---\nname: Nice Name\ntags: [a, b]\ndescription: fm desc\n---\n# hi")
    skill = await upload_skill(tar, None, "desc from form", None, "1.0.0", user, skills_dir)

    assert skill.display_name == "Nice Name"
    assert skill.tags == ["a", "b"]
    assert skill.description == "desc from form"  # 描述仍由表单决定


@pytest.mark.asyncio
async def test_upload_falls_back_when_frontmatter_is_missing(user, skills_dir):
    skill = await upload_skill(make_zip("plain-skill"), None, "d", None, "1.0.0", user, skills_dir)

    assert skill.display_name == "plain-skill"
    assert skill.tags == []


@pytest.mark.asyncio
async def test_upload_explicit_display_name_wins(user, skills_dir):
    """老客户端仍会传这两个字段，必须照旧生效。"""
    tar = make_zip_md("explicit-skill", "---\nname: From Frontmatter\ntags: [fm]\n---\n")
    skill = await upload_skill(tar, "From Form", "d", ["form"], "1.0.0", user, skills_dir)

    assert skill.display_name == "From Form"
    assert skill.tags == ["form"]


# ---------------------------------------------------------------------------
# 名称只在作者内唯一
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_local_upload_same_name_other_author_is_allowed(user, skills_dir):
    other = await User.create(username="other", password_hash="x", status="active")
    mine = await upload_skill(make_zip("shared-name"), "Mine", "d", [], "1.0.0", user, skills_dir)
    theirs = await upload_skill(make_zip("shared-name"), "Theirs", "d", [], "1.0.0", other, skills_dir)

    assert mine.id != theirs.id
    assert await Skill.filter(name="shared-name").count() == 2
    # 磁盘上各占一层作者目录，不能互相踩
    assert (skills_dir / UPLOADER / "shared-name" / "1.0.0" / "SKILL.md").exists()
    assert (skills_dir / "other" / "shared-name" / "1.0.0" / "SKILL.md").exists()


@pytest.mark.asyncio
async def test_local_upload_same_author_same_name_appends_version(user, skills_dir):
    """同作者同名仍是一条记录、追加版本 —— 这条老行为不能被放松掉。"""
    await upload_skill(make_zip("mine"), "Mine", "d", [], "1.0.0", user, skills_dir)
    again = await upload_skill(make_zip("mine"), "Mine", "d", [], "1.1.0", user, skills_dir)

    assert await Skill.filter(name="mine").count() == 1
    assert await SkillVersion.filter(skill=again).count() == 2


# ---------------------------------------------------------------------------
# 转让：目标撞名时必须原地拦下，不能把文件搬坏
# ---------------------------------------------------------------------------

@pytest.fixture
def cwd_skills(tmp_path, monkeypatch):
    """transfer/delete 内部自己 new 了 Config()，工作目录就是它的 base_dir。"""
    monkeypatch.chdir(tmp_path)
    return tmp_path / "skills"


@pytest.mark.asyncio
async def test_transfer_rejected_when_target_has_same_name(user, cwd_skills):
    from skillhub_selfhost.skills.service import transfer_skill
    other = await User.create(username="other", password_hash="x", status="active")
    await upload_skill(make_zip("dup"), "Dup", "d", [], "1.0.0", user, cwd_skills)
    await Skill.create(name="dup", display_name="Theirs", description="", tags=[], author=other)

    with pytest.raises(ConflictError, match="已有同名 skill"):
        await transfer_skill(UPLOADER, "dup", "other", user)

    # 拦在搬文件之前
    assert (cwd_skills / UPLOADER / "dup" / "1.0.0" / "SKILL.md").exists()
    assert (await Skill.filter(author=user, name="dup").first()) is not None


@pytest.mark.asyncio
async def test_transfer_rejected_when_target_dir_exists(user, cwd_skills):
    """DB 里没有同名，但磁盘上已经有同名目录 —— 搬过去会套娃成 dup/dup。"""
    from skillhub_selfhost.skills.service import transfer_skill
    await User.create(username="other", password_hash="x", status="active")
    await upload_skill(make_zip("dup"), "Dup", "d", [], "1.0.0", user, cwd_skills)
    (cwd_skills / "other" / "dup").mkdir(parents=True, exist_ok=True)

    with pytest.raises(ConflictError, match="目录已存在"):
        await transfer_skill(UPLOADER, "dup", "other", user)

    assert (cwd_skills / UPLOADER / "dup" / "1.0.0" / "SKILL.md").exists()
    assert not (cwd_skills / "other" / "dup" / "dup").exists()


@pytest.mark.asyncio
async def test_transfer_moves_files_and_updates_author(user, cwd_skills):
    from skillhub_selfhost.skills.service import transfer_skill
    other = await User.create(username="other", password_hash="x", status="active")
    await upload_skill(make_zip("movable"), "Movable", "d", [], "1.0.0", user, cwd_skills)

    await transfer_skill(UPLOADER, "movable", "other", user)

    assert (cwd_skills / "other" / "movable" / "1.0.0" / "SKILL.md").exists()
    assert not (cwd_skills / UPLOADER / "movable").exists()
    moved = await Skill.filter(name="movable").first()
    assert moved.author_id == other.id
