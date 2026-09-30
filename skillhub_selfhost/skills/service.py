# skillhub_selfhost/skills/service.py
from __future__ import annotations

import io
import zipfile
import re
import shutil
import os
from pathlib import Path
from tortoise.expressions import Q
from skillhub_selfhost.skills import remote
from skillhub_selfhost.skills.errors import ConflictError, RemoteFetchError, ValidationError
from skillhub_selfhost.skills.models import SOURCE_GITLAB, SOURCE_LOCAL, Skill, SkillVersion, DownloadLog
from skillhub_selfhost.skills.skillmd import derive_meta
from skillhub_selfhost.auth.models import User
from skillhub_selfhost.config import Config

SKILL_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

# 远程 skill 没有版本概念，DownloadLog.version 用空串占位（字段非空）
REMOTE_VERSION = ""


def _extract_skill_name_from_zip(file_content: bytes) -> str:
    buf = io.BytesIO(file_content)
    with zipfile.ZipFile(buf) as zf:
        for name in zf.namelist():
            parts = name.split("/", 1)
            if len(parts) >= 2 and parts[1] == "SKILL.md":
                return parts[0]
    raise ValueError("zip 内必须包含 SKILL.md，且文件需放在以 skill 名称命名的根目录下")


def _read_zip_skill_md(file_content: bytes, skill_name: str) -> str:
    """读 zip 里 <skill_name>/SKILL.md 的文本（_extract_skill_name_from_zip 已保证其存在）。"""
    with zipfile.ZipFile(io.BytesIO(file_content)) as zf:
        return zf.read(f"{skill_name}/SKILL.md").decode("utf-8", errors="replace")


def _validate_skill_name(name: str):
    if not SKILL_NAME_RE.match(name) or len(name) > 128:
        raise ValueError("skill 名称不合法，需以字母或数字开头，仅含字母、数字、连字符、下划线、点号")


def _validate_version(version: str):
    if not SEMVER_RE.match(version):
        raise ValueError("版本号格式不正确，请使用 x.y.z 格式")


def _bump_patch(version: str) -> str:
    parts = version.split(".")
    return f"{parts[0]}.{parts[1]}.{int(parts[2]) + 1}"


async def _find_skill(username: str, name: str) -> Skill | None:
    """按「作者 + 名称」定位 skill —— 名称只在作者内唯一，光有 name 找不到唯一的一条。"""
    return await Skill.filter(author__username=username, name=name).prefetch_related("author").first()


async def upload_skill(
    file_content: bytes,
    display_name: str | None,
    description: str,
    tags: list[str] | None,
    version: str,
    author: User,
    skills_dir: Path,
    release_notes: str | None = None,
    original_author: str | None = None,
    source_url: str | None = None,
) -> Skill:
    skill_name = _extract_skill_name_from_zip(file_content)
    _validate_skill_name(skill_name)

    # 表单不再填展示名与标签，缺省时和 GitLab 那条路径一样从 SKILL.md 的 frontmatter 取
    if not display_name or not tags:
        fm_name, _, fm_tags = derive_meta(_read_zip_skill_md(file_content, skill_name), skill_name)
        display_name = display_name or fm_name
        tags = tags or fm_tags

    # 只认自己名下的同名 skill：别人叫这个名字是另一个 skill，不构成冲突
    existing = await Skill.filter(author=author, name=skill_name).prefetch_related("author").first()
    if existing and existing.source_type != SOURCE_LOCAL:
        raise ConflictError("同名远程 skill 已存在，远程 skill 不支持通过本地上传追加版本")

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
        existing.display_name = display_name
        existing.description = description
        existing.tags = tags
        existing.original_author = original_author
        existing.source_url = source_url
        await existing.save()
    else:
        existing = await Skill.create(
            name=skill_name,
            display_name=display_name,
            description=description,
            tags=tags,
            author=author,
            original_author=original_author,
            source_url=source_url,
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


async def _record_download(skill: Skill, version: str):
    skill.download_count += 1
    await skill.save()
    await DownloadLog.create(skill=skill, version=version)


async def upload_remote_skill(gitlab_url: str, branch: str, skill_path: str, author: User) -> Skill:
    """登记一个 GitLab 仓库中的 skill（不落盘、不建版本、不缓存内容）。"""
    ref = remote.parse_project_url(gitlab_url)
    path = remote.normalize_skill_path(skill_path)
    branch = remote.validate_branch(branch)

    # 路径留空（或填 .）表示 skill 就在仓库根目录，此时用项目名作为 skill 名称
    skill_name = path.rsplit("/", 1)[-1] if path else ref.project_path.rsplit("/", 1)[-1]
    _validate_skill_name(skill_name)

    skill_md = await remote.fetch_skill_md(ref, branch, path)
    display_name, description, tags = derive_meta(skill_md, skill_name)

    # 同上：只查自己名下的同名 skill
    existing = await Skill.filter(author=author, name=skill_name).prefetch_related("author").first()
    if existing is None:
        return await Skill.create(
            name=skill_name,
            display_name=display_name,
            description=description,
            tags=tags,
            author=author,
            source_url=ref.project_url,
            source_type=SOURCE_GITLAB,
            source_branch=branch,
            source_path=path,
        )

    if existing.source_type != SOURCE_GITLAB:
        # 不静默转换：本地 skill 有磁盘文件和版本历史，转成远程会把它们遗留成孤儿
        raise ConflictError("同名本地 skill 已存在，请先删除，或调整 GitLab 中的文件夹名")

    # 同作者且已是远程 skill：幂等重新指向，顺便刷新元数据
    existing.display_name = display_name
    existing.description = description
    existing.tags = tags
    existing.source_url = ref.project_url
    existing.source_branch = branch
    existing.source_path = path
    await existing.save()
    return existing


def _skill_payload(skill: Skill, latest_version: str) -> dict:
    return {
        "name": skill.name,
        "display_name": skill.display_name,
        "description": skill.description,
        "author": {"username": skill.author.username, "status": skill.author.status},
        "original_author": skill.original_author,
        "source_url": skill.source_url,
        "source_type": skill.source_type,
        "source_branch": skill.source_branch,
        "source_path": skill.source_path,
        "latest_version": latest_version,
        "tags": skill.tags,
        "download_count": skill.download_count,
        "created_at": skill.created_at,
        "updated_at": skill.updated_at,
    }


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
        items.append(_skill_payload(s, await _latest_version(s)))
    return items, total


async def _latest_version(skill: Skill) -> str:
    """远程 skill 没有版本，直接跳过查询。"""
    if skill.source_type == SOURCE_GITLAB:
        return ""
    latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
    return latest.version if latest else ""


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
        items.append(_skill_payload(s, await _latest_version(s)))
    return items, total


async def get_skill_detail(username: str, name: str) -> dict | None:
    skill = await _find_skill(username, name)
    if not skill:
        return None
    if skill.source_type == SOURCE_GITLAB:
        versions = []
    else:
        versions = await SkillVersion.filter(skill=skill).order_by("-created_at").all()
    detail = _skill_payload(skill, versions[0].version if versions else "")
    detail.pop("latest_version")
    detail["versions"] = [
        {"version": v.version, "release_notes": v.release_notes, "file_size": v.file_size, "created_at": v.created_at}
        for v in versions
    ]
    return detail


async def get_skill_readme(username: str, name: str, version: str | None = None,
                           skills_dir: Path | None = None) -> str:
    skill = await _find_skill(username, name)
    if not skill:
        raise ValueError("skill 不存在")

    if skill.source_type == SOURCE_GITLAB:
        # 远程 skill 不缓存：每次查看都实时读取仓库中最新的 SKILL.md
        ref = remote.parse_project_url(skill.source_url or "")
        return await remote.fetch_skill_md(ref, skill.source_branch or "", skill.source_path or "")

    if not version:
        latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
        if not latest:
            raise ValueError("没有版本")
        version = latest.version
    if skills_dir is None:
        skills_dir = Path.cwd() / "skills"
    readme_path = skills_dir / skill.author.username / skill.name / version / "SKILL.md"
    if not readme_path.exists():
        raise ValueError("SKILL.md 不存在")
    return readme_path.read_text(encoding="utf-8")


async def download_skill(username: str, name: str, version: str | None = None,
                         skills_dir: Path | None = None) -> tuple[Path | None, str, bytes]:
    skill = await _find_skill(username, name)
    if not skill:
        raise ValueError("skill 不存在")

    if skill.source_type == SOURCE_GITLAB:
        ref = remote.parse_project_url(skill.source_url or "")
        archive = await remote.fetch_archive(ref, skill.source_branch or "", skill.source_path or "")
        content = remote.repack_archive(archive, skill.name, skill.source_path or "")
        await _record_download(skill, REMOTE_VERSION)
        return None, f"{skill.name}.zip", content

    if not version:
        latest = await SkillVersion.filter(skill=skill).order_by("-created_at").first()
        if not latest:
            raise ValueError("没有版本")
        version = latest.version
    if skills_dir is None:
        skills_dir = Path.cwd() / "skills"

    src_dir = skills_dir / skill.author.username / skill.name / version
    if not src_dir.exists():
        raise ValueError("版本文件不存在")

    content = remote.build_zip_from_dir(src_dir, skill.name)
    await _record_download(skill, version)

    filename = f"{skill.name}-v{version}.zip"
    return src_dir, filename, content


async def delete_skill(username: str, name: str, author: User):
    skill = await _find_skill(username, name)
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != author.id:
        raise ValueError("无权限删除此 skill")

    config = Config()
    skill_dir = config.skills_dir / skill.author.username / skill.name
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    await skill.delete()


async def delete_skill_version(username: str, name: str, version: str, author: User):
    skill = await _find_skill(username, name)
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != author.id:
        raise ValueError("无权限删除此版本")
    if skill.source_type == SOURCE_GITLAB:
        raise ValueError("远程 skill 没有版本，无法删除版本")

    ver = await SkillVersion.filter(skill=skill, version=version).first()
    if not ver:
        raise ValueError("版本不存在")

    config = Config()
    version_dir = config.skills_dir / skill.author.username / skill.name / version
    if version_dir.exists():
        shutil.rmtree(version_dir)
    await ver.delete()

    remaining = await SkillVersion.filter(skill=skill).count()
    if remaining == 0:
        skill_dir = config.skills_dir / skill.author.username / skill.name
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
        await skill.delete()


async def transfer_skill(username: str, name: str, target_username: str, actor: User):
    skill = await _find_skill(username, name)
    if not skill:
        raise ValueError("skill 不存在")
    if skill.author_id != actor.id and not actor.is_admin:
        raise ValueError("无权限转移此 skill")

    target = await User.filter(username=target_username, status="active").first()
    if not target:
        raise ValueError(f"用户 {target_username} 不存在或未激活")

    # 目标已经有同名 skill / 同名目录时会撞 (author_id, name) 唯一约束，
    # 或把文件搬成 <dir>/<name>/<name> 套娃，所以先拦住
    if await Skill.filter(author=target, name=skill.name).exists():
        raise ConflictError("目标用户已有同名 skill，无法转让")

    config = Config()
    old_dir = config.skills_dir / skill.author.username / skill.name
    new_dir = config.skills_dir / target_username
    if (new_dir / skill.name).exists():
        raise ConflictError("目标用户的技能目录已存在，无法转让")

    new_dir.mkdir(parents=True, exist_ok=True)
    if old_dir.exists():
        shutil.move(str(old_dir), str(new_dir / skill.name))

    skill.author_id = target.id
    await skill.save()