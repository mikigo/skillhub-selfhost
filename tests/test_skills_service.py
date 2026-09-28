# tests/test_skills_service.py
import io
import tarfile
import pytest
from skillhub_selfhost.skills.service import upload_skill
from skillhub_selfhost.skills.models import Skill, SkillVersion
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config


def make_tar(skill_name: str, has_skill_md: bool = True) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        if has_skill_md:
            content = b"# Test"
            info = tarfile.TarInfo(name=f"{skill_name}/SKILL.md")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))
    return buf.getvalue()


@pytest.fixture
def config():
    return Config()


@pytest.fixture
async def user():
    return await User.create(username="uploader", password_hash="x", status="active")


@pytest.mark.asyncio
async def test_upload_new_skill(config, user, skills_dir):
    tar_bytes = make_tar("my-linter")
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
    tar_bytes = make_tar("bad-skill", has_skill_md=False)
    with pytest.raises(ValueError, match="必须包含 SKILL.md"):
        await upload_skill(tar_bytes, "Bad", "desc", [], "1.0.0", user, skills_dir)


@pytest.mark.asyncio
async def test_upload_duplicate_version(config, user, skills_dir):
    tar_bytes = make_tar("dup-skill")
    await upload_skill(tar_bytes, "Dup", "desc", [], "1.0.0", user, skills_dir)
    with pytest.raises(ValueError, match="已存在"):
        await upload_skill(tar_bytes, "Dup2", "desc2", [], "1.0.0", user, skills_dir)


@pytest.mark.asyncio
async def test_upload_auto_version(config, user, skills_dir):
    tar_bytes = make_tar("auto-skill")
    await upload_skill(tar_bytes, "Auto", "desc", [], "1.0.0", user, skills_dir)
    skill2 = await upload_skill(tar_bytes, "Auto", "desc", [], "", user, skills_dir)
    versions = await SkillVersion.filter(skill__name="auto-skill").all()
    assert len(versions) == 2
    assert versions[1].version == "1.0.1"


@pytest.mark.asyncio
async def test_list_skills(config, user):
    tar = make_tar("list-skill")
    await upload_skill(tar, "List Skill", "desc", ["python"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import list_skills
    items, total = await list_skills(page=1, size=20)
    assert total >= 1


@pytest.mark.asyncio
async def test_search_skills(config, user):
    tar = make_tar("search-skill")
    await upload_skill(tar, "Search Skill", "a unique desc word", ["go"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import search_skills
    items, total = await search_skills(q="unique desc")
    assert total >= 1


@pytest.mark.asyncio
async def test_filter_by_tag(config, user):
    tar1 = make_tar("tag-a")
    tar2 = make_tar("tag-b")
    await upload_skill(tar1, "Tag A", "desc", ["python", "linter"], "1.0.0", user, config.skills_dir)
    await upload_skill(tar2, "Tag B", "desc", ["python"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import search_skills
    items, _ = await search_skills(tags=["python", "linter"])
    assert len(items) >= 1


@pytest.mark.asyncio
async def test_download_increments_count(config, user):
    tar = make_tar("dl-count")
    await upload_skill(tar, "DL Count", "desc", [], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import download_skill
    path, filename, content = await download_skill("dl-count")
    skill = await Skill.filter(name="dl-count").first()
    assert skill.download_count == 1


@pytest.mark.asyncio
async def test_get_skill_detail(config, user):
    tar = make_tar("detail-test")
    await upload_skill(tar, "Detail Test", "desc", ["x"], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import get_skill_detail
    detail = await get_skill_detail("detail-test")
    assert detail["name"] == "detail-test"
    assert len(detail["versions"]) == 1


@pytest.mark.asyncio
async def test_get_readme(config, user):
    tar = make_tar("readme-test")
    await upload_skill(tar, "Readme Test", "desc", [], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import get_skill_readme
    content = await get_skill_readme("readme-test", skills_dir=config.skills_dir)
    assert "# Test" in content


@pytest.mark.asyncio
async def test_delete_skill(config, user):
    tar = make_tar("delete-test")
    await upload_skill(tar, "Delete", "desc", [], "1.0.0", user, config.skills_dir)
    from skillhub_selfhost.skills.service import delete_skill
    await delete_skill("delete-test", user)
    s = await Skill.filter(name="delete-test").first()
    assert s is None