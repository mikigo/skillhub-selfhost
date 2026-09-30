# skillhub_selfhost/skills/skillmd.py
"""SKILL.md 清单文件：文件名常量与 frontmatter 解析。

跟内容是从本地 ZIP 来的还是从 GitLab 来的无关，所以不放在 remote.py 里。
"""
from __future__ import annotations

# 大小写两种写法都接受（Windows 上常见 SKILL.md，部分仓库写 skill.md）
SKILL_MD_NAMES = ("SKILL.md", "skill.md")

_BLOCK_SCALARS = ("|", ">", "|-", ">-", "|+", ">+")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    """解析 SKILL.md 的 YAML frontmatter。

    只认识这个场景需要的子集：单行标量、行内/逗号列表、块状列表、块标量（| 与 >）。
    刻意不引入 PyYAML —— 依赖列表保持精简。
    """
    if not text:
        return {}
    lines = text.lstrip("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    frontmatter: dict = {}
    current_list_key: str | None = None
    i = 1
    while i < len(lines):
        raw = lines[i]
        stripped = raw.strip()
        i += 1

        if stripped in ("---", "..."):
            break
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("-") and (stripped == "-" or stripped[1:2] in ("", " ", "\t")):
            if current_list_key and isinstance(frontmatter.get(current_list_key), list):
                item = _unquote(stripped[1:].strip())
                if item:
                    frontmatter[current_list_key].append(item)
            continue

        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        current_list_key = None

        if not value:
            # 空值：向后看一行判断是不是块状列表
            j = i
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines) and lines[j].strip().startswith("-"):
                frontmatter[key] = []
                current_list_key = key
            else:
                frontmatter[key] = ""
            continue

        if value in _BLOCK_SCALARS:
            block: list[str] = []
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() and not nxt.startswith((" ", "\t")):
                    break
                block.append(nxt)
                i += 1
            indent = next((len(x) - len(x.lstrip()) for x in block if x.strip()), 0)
            if indent:
                block = [x[indent:] if x.strip() else "" for x in block]
            if value.startswith(">"):
                frontmatter[key] = " ".join(x.strip() for x in block).strip()
            else:
                frontmatter[key] = "\n".join(block).strip()
            continue

        if value.startswith("[") and value.endswith("]"):
            frontmatter[key] = _split_list(value[1:-1])
        elif "," in value:
            frontmatter[key] = _split_list(value)
        else:
            frontmatter[key] = _unquote(value)
    return frontmatter


def _split_list(value: str) -> list[str]:
    return [v for v in (_unquote(x.strip()) for x in value.split(",")) if v]


def _as_str(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [x.strip() for x in value if isinstance(x, str) and x.strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def derive_meta(skill_md: str, fallback_name: str) -> tuple[str, str, list[str]]:
    """从 SKILL.md 派生 (display_name, description, tags)。"""
    frontmatter = parse_frontmatter(skill_md)
    name = _as_str(frontmatter.get("name")) or fallback_name
    description = _as_str(frontmatter.get("description"))
    tags = _as_list(frontmatter.get("tags"))
    return name[:256], description, tags
