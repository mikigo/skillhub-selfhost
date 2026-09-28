# skillhub_selfhost/skills/service.py
import io
import tarfile
import re
from pathlib import Path
from skillhub_selfhost.skills.models import Skill, SkillVersion
from skillhub_selfhost.auth.models import User

SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _extract_skill_name_from_tar(file_content: bytes) -> str:
    buf = io.BytesIO(file_content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            parts = member.name.split("/", 1)
            if len(parts) >= 2 and parts[1] == "SKILL.md":
                return parts[0]
    raise ValueError("tar.gz 内必须包含 SKILL.md，且文件需放在以 skill 名称命名的根目录下")


def _validate_skill_name(name: str):
    if not SKILL_NAME_RE.match(name) or len(name) > 128:
        raise ValueError("skill 名称不合法，需以字母或数字开头，仅含字母、数字、连字符、下划线、点号")


def _validate_version(version: str):
    if not SEMVER_RE.match(version):
        raise ValueError("版本号格式不正确，请使用 x.y.z 格式")


def _bump_patch(version: str) -> str:
    parts = version.split(".")
    return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"


async def upload_skill(
    file_content: bytes,
    display_name: str,
    description: str,
    tags: list[str],
    version: str,
    author: User,
    skills_dir: Path,
    release_notes: str | None = None,
) -> Skill:
    skill_name = _extract_skill_name_from_tar(file_content)
    _validate_skill_name(skill_name)

    existing = await Skill.filter(name=skill_name).prefetch_related("author").first()
    if existing and existing.author_id != author.id:
        raise ValueError("skill 名称已被占用")

    if not version:
        if existing:
            latest = await SkillVersion.filter(skill=existing).order_by("-created_at").first()
            version = _bump_patch(latest.version)
        else:
            version = "1.0.0"
    _validate_version(version)

    if existing:
        dup = await SkillVersion.filter(skill=existing, version=version).first()
        if dup:
            raise ValueError(f"版本 {version} 已存在")
    else:
        existing = await Skill.create(
            name=skill_name,
            display_name=display_name,
            description=description,
            tags=tags,
            author=author,
        )

    file_size = len(file_content)

    version_dir = skills_dir / author.username / skill_name / version
    version_dir.mkdir(parents=True, exist_ok=True)

    buf = io.BytesIO(file_content)
    with tarfile.open(fileobj=buf, mode="r:gz") as tar:
        for member in tar.getmembers():
            rel = member.name[len(skill_name) + 1:]
            if not rel or ".." in rel or rel.startswith("/"):
                continue
            target = version_dir / rel
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src:
                    target.write_bytes(src.read())

    await SkillVersion.create(
        skill=existing,
        version=version,
        release_notes=release_notes,
        file_size=file_size,
    )

    return existing