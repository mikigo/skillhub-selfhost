# tests/test_skillmd.py
"""skillmd.py 的纯函数测试：不联网、不连库。"""
from skillhub_selfhost.skills import skillmd


def test_skill_md_names():
    assert skillmd.SKILL_MD_NAMES == ("SKILL.md", "skill.md")


def test_frontmatter_scalars_and_lists():
    fm = skillmd.parse_frontmatter("---\nname: Foo Bar\ndescription: A linter\ntags: [python, lint]\n---\n# body")
    assert fm["name"] == "Foo Bar"
    assert fm["description"] == "A linter"
    assert fm["tags"] == ["python", "lint"]
    assert skillmd.parse_frontmatter("---\ntags: a, b\n---\n")["tags"] == ["a", "b"]
    assert skillmd.parse_frontmatter("---\ntags:\n  - a\n  - b\n---\n")["tags"] == ["a", "b"]


def test_frontmatter_quoting_and_whitespace():
    assert skillmd.parse_frontmatter('---\nname: "Q"\n---\n')["name"] == "Q"
    assert skillmd.parse_frontmatter("---\r\nname: Win\r\n---\r\n")["name"] == "Win"
    assert skillmd.parse_frontmatter("\ufeff---\nname: Bom\n---\n")["name"] == "Bom"


def test_frontmatter_absent_or_unterminated():
    assert skillmd.parse_frontmatter("no frontmatter") == {}
    assert skillmd.parse_frontmatter("") == {}
    assert skillmd.parse_frontmatter("---\nname: X\n---\nbody\n---\nmore")["name"] == "X"


def test_frontmatter_block_scalars():
    assert skillmd.parse_frontmatter("---\ndescription: |\n  line one\n  line two\n---\n")["description"] == "line one\nline two"
    assert skillmd.parse_frontmatter("---\ndescription: >\n  a\n  b\n---\n")["description"] == "a b"
    assert skillmd.parse_frontmatter("---\nempty:\nname: X\n---\n")["empty"] == ""


def test_derive_meta():
    assert skillmd.derive_meta("---\nname: N\ndescription: D\ntags: [t]\n---", "fb") == ("N", "D", ["t"])
    assert skillmd.derive_meta("no fm", "fb") == ("fb", "", [])
    assert skillmd.derive_meta("---\ntags: x\n---", "fb")[0] == "fb"
    assert len(skillmd.derive_meta("---\nname: " + "x" * 300 + "\n---", "fb")[0]) == 256
