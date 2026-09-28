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