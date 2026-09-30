# tests/test_remote_unit.py
"""remote.py 的纯函数测试：不联网、不连库。"""
import io
import zipfile

import pytest

from skillhub_selfhost.skills import remote
from skillhub_selfhost.skills.errors import RemoteFetchError, ValidationError

SKILL_MD = "---\nname: Foo\ndescription: d\n---\n# hi"


def make_zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return buf.getvalue()


# --------------------------------------------------------------------------
# parse_project_url
# --------------------------------------------------------------------------

def test_parse_url_variants():
    assert remote.parse_project_url("https://gitlab.com/group/proj").project_path == "group/proj"
    assert remote.parse_project_url("https://gitlab.com/group/proj.git").project_path == "group/proj"
    assert remote.parse_project_url("https://gitlab.com/group/proj/").project_url == "https://gitlab.com/group/proj"
    assert remote.parse_project_url("gitlab.com/a/b").api_base == "https://gitlab.com/api/v4"
    assert remote.parse_project_url("http://gl.internal:8080/a/b").base_url == "http://gl.internal:8080"


def test_parse_url_strips_browser_suffix():
    ref = remote.parse_project_url("https://gitlab.com/group/proj/-/tree/main/skills/foo")
    assert ref.project_path == "group/proj"
    assert ref.project_url == "https://gitlab.com/group/proj"


@pytest.mark.parametrize("bad", ["ftp://h/a/b", "https:///a/b", "https://u:p@h/a/b", "", "https://h"])
def test_parse_url_rejects(bad):
    with pytest.raises(ValidationError):
        remote.parse_project_url(bad)


# --------------------------------------------------------------------------
# normalize_skill_path / validate_branch
# --------------------------------------------------------------------------

def test_normalize_skill_path():
    assert remote.normalize_skill_path("agents/foo") == "agents/foo"
    assert remote.normalize_skill_path("/agents/foo/") == "agents/foo"
    assert remote.normalize_skill_path("a//b") == "a/b"
    assert remote.normalize_skill_path(".") == ""
    assert remote.normalize_skill_path("./") == ""
    assert remote.normalize_skill_path("") == ""


@pytest.mark.parametrize("bad", ["../x", "a/../../b", "a\\b", "x\x00y"])
def test_normalize_skill_path_rejects(bad):
    with pytest.raises(ValidationError):
        remote.normalize_skill_path(bad)


@pytest.mark.parametrize("ok", ["main", "release/1.0", "feature_x-1.2"])
def test_validate_branch_ok(ok):
    assert remote.validate_branch(ok) == ok


@pytest.mark.parametrize("bad", ["", "   ", "a b", "a..b", "a&b", "-x"])
def test_validate_branch_rejects(bad):
    with pytest.raises(ValidationError):
        remote.validate_branch(bad)


# --------------------------------------------------------------------------
# repack_archive
# --------------------------------------------------------------------------

SHAPES = {
    # path 被 git archive 当成 <ref>:<path>，归档根下面直接就是 SKILL.md
    "path-replaced": [("proj-main-abc/SKILL.md", SKILL_MD), ("proj-main-abc/run.sh", "x")],
    # path 作为 pathspec，保留在归档内
    "path-as-pathspec": [("proj-main-abc/agents/foo/SKILL.md", SKILL_MD), ("proj-main-abc/agents/foo/a.txt", "1")],
    # 老版本 GitLab 忽略 path，返回整仓
    "path-ignored": [("proj-main-abc/other/x.md", "o"), ("proj-main-abc/agents/foo/SKILL.md", SKILL_MD),
                     ("proj-main-abc/agents/foo/a.txt", "1")],
    # 没有归档根目录
    "no-root-prefix": [("agents/foo/SKILL.md", SKILL_MD), ("agents/foo/a.txt", "1")],
}


@pytest.mark.parametrize("shape", list(SHAPES))
def test_repack_all_archive_shapes(shape):
    out = remote.repack_archive(make_zip(SHAPES[shape]), "foo", "agents/foo")
    names = sorted(zipfile.ZipFile(io.BytesIO(out)).namelist())
    assert "foo/SKILL.md" in names
    assert all(n.startswith("foo/") for n in names)
    assert not any("proj-main" in n or "agents/foo" in n for n in names)


def test_repack_skill_at_repo_root():
    out = remote.repack_archive(make_zip([("proj-main-abc/SKILL.md", SKILL_MD)]), "root-skill", "")
    assert sorted(zipfile.ZipFile(io.BytesIO(out)).namelist()) == ["root-skill/SKILL.md"]


def test_repack_prefers_subpath_over_repo_root_skill_md():
    """仓库根目录恰好也有 SKILL.md 时，必须选中 skill_path 下的那个。"""
    entries = [("proj-main-abc/SKILL.md", "ROOT"), ("proj-main-abc/agents/foo/SKILL.md", "SUB")]
    out = remote.repack_archive(make_zip(entries), "foo", "agents/foo")
    names = zipfile.ZipFile(io.BytesIO(out)).namelist()
    assert names == ["foo/SKILL.md"]
    assert zipfile.ZipFile(io.BytesIO(out)).read("foo/SKILL.md") == b"SUB"


def test_repack_drops_unsafe_entries():
    entries = [
        ("proj-main-abc/SKILL.md", SKILL_MD),
        ("proj-main-abc/../../etc/passwd", "bad"),
        ("proj-main-abc//abs", "bad"),
        ("proj-main-abc/sub/", ""),  # 目录条目
    ]
    out = remote.repack_archive(make_zip(entries), "foo", "")
    assert sorted(zipfile.ZipFile(io.BytesIO(out)).namelist()) == ["foo/SKILL.md"]


@pytest.mark.parametrize("entries", [[], [("proj-main-abc/readme.md", "x")]])
def test_repack_raises_when_no_root_skill_md(entries):
    with pytest.raises(RemoteFetchError) as exc:
        remote.repack_archive(make_zip(entries), "foo", "")
    assert exc.value.status_code == 502


def test_repack_raises_on_non_zip():
    with pytest.raises(RemoteFetchError):
        remote.repack_archive(b"not a zip", "foo", "")


def test_repack_entry_limit():
    entries = [("proj-main-abc/SKILL.md", SKILL_MD)] + [(f"proj-main-abc/f{i}", "x") for i in range(remote.MAX_ENTRIES)]
    with pytest.raises(RemoteFetchError, match="文件过多"):
        remote.repack_archive(make_zip(entries), "foo", "")


def test_safe_relpath():
    assert remote._safe_relpath("a/b.md") == "a/b.md"
    for bad in ["", "../x", "/abs", "C:/x", "a\\b", "x\x00y", "a//b"]:
        assert remote._safe_relpath(bad) is None
