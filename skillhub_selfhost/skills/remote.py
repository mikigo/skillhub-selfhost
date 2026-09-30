# skillhub_selfhost/skills/remote.py
"""远程引用型 skill：从 GitLab 拉取 SKILL.md 与归档。

本模块只依赖标准库（urllib）做网络请求，通过 run_in_threadpool 放到线程池里执行，
因此不需要引入任何新的依赖。所有远程逻辑集中在这里，后续要支持 GitHub 只需扩展本文件。
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from starlette.concurrency import run_in_threadpool

from skillhub_selfhost.skills.errors import RemoteFetchError, ValidationError
from skillhub_selfhost.skills.skillmd import SKILL_MD_NAMES

logger = logging.getLogger(__name__)

USER_AGENT = "skillhub-selfhost"
MAX_CONCURRENCY = 8
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024        # 从 GitLab 收下来的上限
MAX_TOTAL_UNCOMPRESSED = 200 * 1024 * 1024   # 重新打包时的解压总量上限（zip bomb 防护）
MAX_ENTRIES = 5000
MAX_SKILL_MD_BYTES = 512 * 1024

BRANCH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")

_semaphore = None


def _get_semaphore() -> asyncio.Semaphore:
    """延迟创建，避免在事件循环之外构造 Semaphore。"""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
    return _semaphore


# --------------------------------------------------------------------------
# URL / 路径校验
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GitLabRef:
    base_url: str       # https://gitlab.example.com
    api_base: str       # https://gitlab.example.com/api/v4
    project_path: str   # group/subgroup/project
    project_url: str    # https://gitlab.example.com/group/subgroup/project


def parse_project_url(raw: str) -> GitLabRef:
    url = (raw or "").strip()
    if not url:
        raise ValidationError("GitLab 地址不能为空")
    if "://" not in url:
        url = "https://" + url

    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValidationError("GitLab 地址不合法，仅支持 http/https")
    if not parts.netloc:
        raise ValidationError("GitLab 地址不合法，缺少主机名")
    if "@" in parts.netloc:
        raise ValidationError("GitLab 地址不合法，不支持携带用户名密码")

    path = parts.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    # 浏览器地址栏复制来的链接会带 /-/tree/<branch>/<path> 之类的后缀
    marker = path.find("/-/")
    if marker != -1:
        path = path[:marker]
    path = path.strip("/")
    if not path:
        raise ValidationError("GitLab 地址不合法，缺少项目路径")

    base_url = f"{parts.scheme}://{parts.netloc}"
    return GitLabRef(
        base_url=base_url,
        api_base=f"{base_url}/api/v4",
        project_path=path,
        project_url=f"{base_url}/{path}",
    )


def normalize_skill_path(raw: str) -> str:
    """规范化仓库内的 skill 目录。前后多余的斜杠会被去掉，`..` 一律拒绝。"""
    p = (raw or "").strip().strip("/")
    if p in ("", "."):
        return ""
    if "\\" in p or "\x00" in p:
        raise ValidationError("技能路径不合法，需为仓库内相对路径")
    parts = [x for x in p.split("/") if x not in ("", ".")]
    if any(x == ".." for x in parts):
        raise ValidationError("技能路径不合法，不能包含 ..")
    if not parts:
        return ""
    return "/".join(parts)


def validate_branch(raw: str) -> str:
    branch = (raw or "").strip()
    if not branch:
        raise ValidationError("分支名不能为空")
    if len(branch) > 255 or not BRANCH_RE.match(branch) or ".." in branch or branch.startswith("-"):
        raise ValidationError("分支名不合法")
    return branch


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def _raise_for_status(e: HTTPError, url: str):
    code = e.code
    logger.warning("GitLab 请求失败（%s）：%s", code, url)
    if code in (401, 403, 404):
        # GitLab 对无权限的私有项目也返回 404，统一文案避免泄露项目是否存在
        raise RemoteFetchError(
            "GitLab 项目、分支或路径不存在，或为私有仓库（本功能仅支持公开仓库）", 404
        ) from e
    if code == 429:
        raise RemoteFetchError("GitLab 请求过于频繁，请稍后重试", 503) from e
    raise RemoteFetchError(f"GitLab 返回错误 {code}", 502) from e


def _get_sync(url: str, timeout: float, max_bytes: int) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    try:
        with urlopen(request, timeout=timeout) as resp:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise RemoteFetchError("技能体积超出限制", 502)
                chunks.append(chunk)
            return b"".join(chunks)
    except RemoteFetchError:
        raise
    except HTTPError as e:  # 必须写在 URLError 之前：HTTPError 是它的子类
        _raise_for_status(e, url)
    except (URLError, TimeoutError, OSError, ValueError) as e:
        logger.warning("无法访问 GitLab：%s（%s）", url, e)
        raise RemoteFetchError("无法访问 GitLab，请检查网络或地址", 502) from e


async def get_bytes(url: str, timeout: float, max_bytes: int = MAX_ARCHIVE_BYTES) -> bytes:
    async with _get_semaphore():
        return await run_in_threadpool(_get_sync, url, timeout, max_bytes)


def _raw_file_url(ref: GitLabRef, branch: str, file_path: str) -> str:
    # 项目路径与文件路径都要整体百分号编码（斜杠编成 %2F），否则 GitLab 会当成多级路由
    project = quote(ref.project_path, safe="")
    file = quote(file_path, safe="")
    return f"{ref.api_base}/projects/{project}/repository/files/{file}/raw?" + urlencode({"ref": branch})


def _archive_url(ref: GitLabRef, branch: str, skill_path: str) -> str:
    params = {"sha": branch}
    if skill_path:
        # path 参数是较新版本才有的，老版本会静默忽略并返回整仓，repack_archive 两种都能处理
        params["path"] = skill_path
    return f"{ref.api_base}/projects/{quote(ref.project_path, safe='')}/repository/archive.zip?" + urlencode(params)


async def fetch_skill_md(ref: GitLabRef, branch: str, skill_path: str) -> str:
    last_error: RemoteFetchError | None = None
    for name in SKILL_MD_NAMES:
        file_path = f"{skill_path}/{name}" if skill_path else name
        try:
            data = await get_bytes(_raw_file_url(ref, branch, file_path), timeout=15.0, max_bytes=MAX_SKILL_MD_BYTES)
            return data.decode("utf-8", errors="replace")
        except RemoteFetchError as e:
            last_error = e
            if e.status_code != 404:
                raise
    raise last_error or RemoteFetchError("未找到 SKILL.md", 404)


async def fetch_archive(ref: GitLabRef, branch: str, skill_path: str) -> bytes:
    return await get_bytes(_archive_url(ref, branch, skill_path), timeout=60.0, max_bytes=MAX_ARCHIVE_BYTES)


# --------------------------------------------------------------------------
# 归档重构（把 GitLab 的归档压成 <skill_name>/... 的形态）
# --------------------------------------------------------------------------

def _safe_relpath(rel: str) -> str | None:
    """把归档内的相对路径收敛成安全形式，不安全就返回 None（调用方跳过该条目）。"""
    if not rel or "\\" in rel or "\x00" in rel:
        return None
    parts = rel.split("/")
    if any(p in ("", ".", "..") for p in parts):
        return None
    if ":" in parts[0]:  # Windows 盘符
        return None
    return rel


def _make_arcname(root_name: str, rel: str) -> str:
    return f"{root_name}/{rel}"


def build_zip_from_dir(src_dir: Path, root_name: str) -> bytes:
    """把磁盘目录打成以 root_name 为根的 zip（本地 skill 下载用）。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _dirs, files in os.walk(src_dir):
            for file in files:
                file_path = Path(root) / file
                rel = str(file_path.relative_to(src_dir)).replace(os.sep, "/")
                zf.write(file_path, _make_arcname(root_name, rel))
    return buf.getvalue()


def _strip_root(names: list[str]) -> list[str]:
    """归档根目录（形如 proj-main-abc123/）只有当所有条目共享同一首段时才去掉。"""
    segments = [n.split("/") for n in names]
    if not segments:
        return list(names)
    root = segments[0][0]
    if all(len(s) > 1 and s[0] == root for s in segments):
        return ["/".join(s[1:]) for s in segments]
    return list(names)


def _has_root_skill_md(relpaths: list[str]) -> bool:
    return any(r.lower() == "skill.md" for r in relpaths)


def _under(names: list[str], prefix: str) -> list[tuple[int, str]]:
    """保留 prefix 之下的条目，返回 (原索引, 去掉 prefix 的相对路径)。"""
    out = []
    for i, name in enumerate(names):
        if name == prefix:
            out.append((i, ""))
        elif name.startswith(prefix + "/"):
            out.append((i, name[len(prefix) + 1:]))
    return out


def _select_pairs(names: list[str], skill_path: str) -> list[tuple[int, str]] | None:
    """挑一个去前缀方案：返回 [(原索引, 相对路径)]，都不可用则 None。

    不硬编码前缀模式，而是枚举候选、取第一个「根部有 SKILL.md」的方案。
    这样既不用判断 GitLab 版本，也不可能悄悄产出结构错误的树。
    """
    stripped = _strip_root(names)
    candidates: list[list[tuple[int, str]]] = []

    if skill_path:
        # 1) 先限定到 skill_path 之下，再剥归档根 —— 仓库根目录恰好也有 SKILL.md 时优先这个
        candidates.append([(i, r) for i, r in _under(stripped, skill_path) if r])
        # 2) 有些 GitLab 会把 path 原样拼进归档根，没有公共根可剥
        candidates.append([(i, r) for i, r in _under(names, skill_path) if r])

    # 3) 只剥归档根：path 被 GitLab 当成 git archive 的 <ref>:<path> 处理时就是这种形态
    candidates.append([(i, stripped[i]) for i in range(len(stripped))])

    for candidate in candidates:
        if candidate and _has_root_skill_md([r for _, r in candidate]):
            return candidate
    return None


def repack_archive(archive_bytes: bytes, skill_name: str, skill_path: str) -> bytes:
    """把 GitLab 的归档重新打成以 <skill_name>/ 为根的 zip。"""
    try:
        zin = zipfile.ZipFile(io.BytesIO(archive_bytes))
    except zipfile.BadZipFile as e:
        raise RemoteFetchError("GitLab 返回的内容不是有效的压缩包", 502) from e

    with zin:
        infos = [i for i in zin.infolist() if i.filename and not i.is_dir() and not i.filename.endswith("/")]
        if not infos:
            raise RemoteFetchError("GitLab 返回的压缩包为空", 502)
        if len(infos) > MAX_ENTRIES:
            raise RemoteFetchError(f"技能目录文件过多（超过 {MAX_ENTRIES} 个）", 502)

        selected = _select_pairs([i.filename for i in infos], skill_path)
        if selected is None:
            raise RemoteFetchError("该路径下未找到 SKILL.md", 502)

        out = io.BytesIO()
        total = 0
        written = 0
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
            for index, rel in selected:
                safe = _safe_relpath(rel)
                if safe is None:
                    continue
                data = zin.read(infos[index])
                total += len(data)
                if total > MAX_TOTAL_UNCOMPRESSED:
                    raise RemoteFetchError("技能体积超出限制", 502)
                zout.writestr(_make_arcname(skill_name, safe), data)
                written += 1

        if written == 0:
            raise RemoteFetchError("该路径下未找到有效文件", 502)
        return out.getvalue()
