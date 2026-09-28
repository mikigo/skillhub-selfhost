# skillhub_selfhost/skills/service.py
import io
import zipfile
import re
import shutil
import os
from pathlib import Path
from tortoise.expressions import Q
from skillhub_selfhost.skills.models import Skill, SkillVersion, DownloadLog
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _extract_skill_name_from_zip(file_content: bytes) -> str:
    buf = io.BytesIO(file_content)
    with zipfile.ZipFile(buf) as zf:
        for name in zf.namelist():
            parts = name.split("/", 1)
            if len(parts) >= 2 and parts[1] == "SKILL.md":
                return parts[0]
    raise ValueError("zip 内必须包含 SKILL.md，且文件需放在以 skill 名称命名的根目录下")


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
    skill_name = _extract_skill_name_from_zip(file_content)
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
    with zipfile.ZipFile(buf) as zf:
        for member in zf.namelist():
            rel = member[len(skill_name) + 1:]
            if not rel or ".." in rel or rel.startswith("/"):
                continue
            target = version_dir / rel
            if member.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(zf.read(member))

    await SkillVersion.create(
        skill=existing,
        version=version,
        release_notes=release_notes,
        file_size=file_size,
    )

    return existing


async def list_skills(page: int = 1, size: int = 20, sort: str = "downloads") -> tuple[list[dict], int]:
    qs = Skill.all().prefetch_related("author")
    if sort == "downloads":
        qs = qs.order_by("-download_count")
    elif sort == "newest":
        qs = qs.order_by("-created_at")

    total = await qs.count()
    skills = await qs.offset((page - 1) * size).limit(size).all()

    items = []
    for s in skills:
        latest = await SkillVersion.filter(skill=s).order_by("-created_at").first()
        items.append({
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "author": {"username": s.author.username, "status": s.author.status},
            "latest_version": latest.version if latest else "",
            "tags": s.tags,
            "download_count": s.download_count,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return items, total


async def search_skills(q: str | None = None, tags: list[str] | None = None, author_username: str | None = None,
                        page: int = 1, size: int = 20, sort: str = "downloads") -> tuple[list[dict], int]:
    qs = Skill.all().prefetch_related("author")
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(display_name__icontains=q) | Q(description__icontains=q))
    if author_username:
        qs = qs.filter(author__username=author_username)

    if sort == "downloads":
        qs = qs.order_by("-download_count")
    elif sort == "newest":
        qs = qs.order_by("-created_at")

    skills = await qs.all()
    if tags:
        skills = [s for s in skills if all(tag in (s.tags or []) for tag in tags)]
    total = len(skills)
    skills = skills[(page - 1) * size:(page - 1) * size + size]

    items = []
    for s in skills:
        latest = await SkillVersion.filter(skill=s).order_by("-created_at").first()
        items.append({
            "name": s.name,
            "display_name": s.display_name,
            "description": s.description,
            "author": {"username": s.author.username, "status": s.author.status},
            "latest_version": latest.version if latest else "",
            "tags": s.tags,
            "download_count": s.download_count,
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })
    return items, total


async def get_skill_detail(name: str) -> dict | None:
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        return None
    versions = await SkillVersion.filter(skill=skill).order_by("-created_at").all()
    return {
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "author": {"username": skill.author.username, "status": skill.author.status},
        "tags": skill.tags,
        "download_count": skill.download_count,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
        "versions": [
            {"version": v.version, "release_notes": v.release_notes, "file_size": v.file_size, "created_at": v.created_at}
            for v in versions
        ],
    }


async def get_skill_readme(name: str, version: str | None = None, skills_dir: Path | None = None) -> str:
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if not version:
        latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
        if not latest:
            raise ValueError("没有版本")
        version = latest.version
    if skills_dir is None:
        skills_dir = Path.cwd() / "skills"
    readme_path = skills_dir / skill.author.username / name / version / "SKILL.md"
    if not readme_path.exists():
        raise ValueError("SKILL.md 不存在")
    return readme_path.read_text(encoding="utf-8")


async def download_skill(name: str, version: str | None = None, skills_dir: Path | None = None) -> tuple[Path, str, bytes]:
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if not version:
        latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
        if not latest:
            raise ValueError("没有版本")
        version = latest.version
    if skills_dir is None:
        skills_dir = Path.cwd() / "skills"

    src_dir = skills_dir / skill.author.username / name / version
    if not src_dir.exists():
        raise ValueError("版本文件不存在")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = str(Path(name) / file_path.relative_to(src_dir))
                zf.write(file_path, arcname)

    skill.download_count += 1
    await skill.save()

    await DownloadLog.create(skill=skill, version=version)

    filename = f"{name}-v{version}.zip"
    return src_dir, filename, buf.getvalue()


async def delete_skill(name: str, author: User):
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != author.id:
        raise ValueError("无权限删除此 skill")

    config = Config()
    skill_dir = config.skills_dir / author.username / name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    await skill.delete()


async def delete_skill_version(name: str, version: str, author: User):
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != author.id:
        raise ValueError("无权限删除此版本")

    ver = await SkillVersion.filter(skill=skill, version=version).first()
    if not ver:
        raise ValueError("版本不存在")

    config = Config()
    version_dir = config.skills_dir / author.username / name / version
    if version_dir.exists():
        shutil.rmtree(version_dir)
    await ver.delete()

    remaining = await SkillVersion.filter(skill=skill).count()
    if remaining == 0:
        skill_dir = config.skills_dir / author.username / name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        await skill.delete()


async def transfer_skill(name: str, target_username: str, actor: User):
    skill = await Skill.filter(name=name).prefetch_related("author").first()
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != actor.id and not actor.is_admin:
        raise ValueError("无权限转移此 skill")

    target = await User.filter(username=target_username, status="active").first()
    if not target:
        raise ValueError(f"用户 {target_username} 不存在或未激活")

    config = Config()
    old_dir = config.skills_dir / skill.author.username / name
    new_dir = config.skills_dir / target_username
    new_dir.mkdir(parents=True, exist_ok=True)
    if old_dir.exists():
        shutil.move(str(old_dir), str(new_dir / name))

    skill.author_id = target.id
    await skill.save()