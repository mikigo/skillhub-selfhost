# tests/test_db_migration.py
"""升级路径：老库的 skills 表要在启动时被幂等地补上新列，并把唯一性从
「全局 name」换成「(author_id, name)」。

这是唯一会真正打坏现有部署的环节（generate_schemas 只发 CREATE TABLE IF NOT EXISTS，
既不会给已存在的表加列，更不会改约束），所以单独测。

skills 的重建刻意用一份贴近真实的老表：UUID 文本主键、内联 UNIQUE、外加两个
带 ON DELETE CASCADE 的子表。最容易出事的正是这两张子表 —— 用 ALTER TABLE RENAME
会把它们的 REFERENCES 改写成指向 skills_old，直接 DROP 又会顺着级联删光数据。
"""
import sqlite3
import uuid

import pytest
from tortoise import Tortoise, connections
from tortoise.exceptions import IntegrityError

from skillhub_selfhost.auth.models import User
from skillhub_selfhost.db import _migrate_add_columns, _migrate_skill_name_scope
from skillhub_selfhost.skills.models import DownloadLog, SkillVersion

# 引入之前（改动前）的 skills 表形态
OLD_SCHEMA = """
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(128) NOT NULL UNIQUE,
    display_name VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    tags JSON NOT NULL,
    author_id INT NOT NULL,
    download_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""

# 更贴近线上那份的形状：UUID 主键 + 内联 UNIQUE，且被两张子表用 ON DELETE CASCADE 引用
OLD_SCOPED_SCHEMA = """
CREATE TABLE skills (
    id CHAR(36) NOT NULL PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    display_name VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    tags JSON NOT NULL,
    author_id CHAR(36) NOT NULL REFERENCES "users" ("id") ON DELETE CASCADE,
    download_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL
)
"""

# UUIDField 的列只认真正的 UUID 文本
ALICE = str(uuid.UUID(int=1))
BOB = str(uuid.UUID(int=2))
OLD_SKILL = str(uuid.UUID(int=0x51))
BOB_SKILL = str(uuid.UUID(int=0x52))
DUP_SKILL = str(uuid.UUID(int=0x53))


@pytest.fixture(autouse=True)
async def setup_db():
    """覆盖 conftest 的内存库初始化：本文件自己控制 DB。"""
    yield


@pytest.fixture
async def old_db(tmp_path):
    db_file = tmp_path / "old.db"
    con = sqlite3.connect(str(db_file))
    con.execute(OLD_SCHEMA)
    con.execute(
        "INSERT INTO skills (name, display_name, description, tags, author_id, download_count, created_at, updated_at)"
        " VALUES ('old-skill', 'Old', 'd', '[]', 1, 0, '2024-01-01 00:00:00', '2024-01-01 00:00:00')"
    )
    con.commit()
    con.close()

    db_url = f"sqlite://{db_file}"
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["skillhub_selfhost.auth.models", "skillhub_selfhost.skills.models"]},
    )
    yield db_url
    await Tortoise.close_connections()


@pytest.fixture
async def legacy_db(tmp_path):
    """老形态的库：一条 skill（作者 user-1）＋ 子表各一行数据，已被补过列。"""
    db_file = tmp_path / "legacy.db"
    con = sqlite3.connect(str(db_file))
    con.execute(OLD_SCOPED_SCHEMA)
    con.execute(
        "INSERT INTO skills (id, name, display_name, description, tags, author_id,"
        " download_count, created_at, updated_at)"
        " VALUES (?, 'old-skill', 'Old', 'd', '[]', ?, 7,"
        " '2024-01-01 00:00:00', '2024-01-01 00:00:00')",
        (OLD_SKILL, ALICE),
    )
    con.commit()
    con.close()

    db_url = f"sqlite://{db_file}"
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["skillhub_selfhost.auth.models", "skillhub_selfhost.skills.models"]},
    )
    await Tortoise.generate_schemas()  # 建出 users / skill_versions / download_logs
    # 走一遍真实顺序：先补列（它结尾的 UPDATE 会留下一个隐式事务，重建必须能自己处理）
    await _migrate_add_columns(db_url)

    await User.create(id=ALICE, username="alice", password_hash="x", status="active")
    await User.create(id=BOB, username="bob", password_hash="x", status="active")
    await SkillVersion.create(skill_id=OLD_SKILL, version="1.0.0", file_size=10)
    await DownloadLog.create(skill_id=OLD_SKILL, version="1.0.0")

    yield db_url
    await Tortoise.close_connections()


async def _unique_indexes(conn, table="skills"):
    """表上所有唯一索引的列组合。"""
    result = []
    _, indexes = await conn.execute_query(f"PRAGMA index_list('{table}')")
    for row in indexes:
        if not row[2]:
            continue
        _, columns = await conn.execute_query(f"PRAGMA index_info('{row[1]}')")
        result.append([c[2] for c in columns])
    return result


async def _table_sql(conn, table):
    _, rows = await conn.execute_query(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", [table]
    )
    return rows[0][0] if rows else None


async def _scalar(conn, sql):
    _, rows = await conn.execute_query(sql)
    return rows[0][0]


async def _add_skill(conn, skill_id, name, author_id):
    await conn.execute_query(
        "INSERT INTO skills (id, name, display_name, description, tags, source_type,"
        " download_count, created_at, updated_at, author_id)"
        " VALUES (?, ?, 'D', 'd', '[]', 'local', 0, '2024-01-01 00:00:00',"
        " '2024-01-01 00:00:00', ?)",
        [skill_id, name, author_id],
    )


# --------------------------------------------------------------------------
# 补列（原有行为）
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_migration_adds_columns_and_backfills(old_db):
    await _migrate_add_columns(old_db)

    conn = connections.get("default")
    # 只要有一个列不存在这里就会抛 OperationalError
    _, rows = await conn.execute_query(
        "SELECT source_type, source_branch, source_path, original_author, source_url FROM skills"
    )
    assert rows[0][0] == "local"
    assert rows[0][1] is None
    assert rows[0][2] is None


@pytest.mark.asyncio
async def test_migration_is_idempotent(old_db):
    await _migrate_add_columns(old_db)
    await _migrate_add_columns(old_db)  # 再跑一次不能炸

    _, rows = await connections.get("default").execute_query("SELECT source_type FROM skills")
    assert rows[0][0] == "local"


@pytest.mark.asyncio
async def test_migration_survives_already_migrated_table(old_db):
    """模型建表时已有全部列（全新安装的场景）时，补列不能报错。"""
    await connections.get("default").execute_query("DROP TABLE skills")
    await Tortoise.generate_schemas()  # 这次建出来的是新表
    await _migrate_add_columns(old_db)  # 每列都已存在，重复 ALTER 必须被吞掉

    _, rows = await connections.get("default").execute_query("SELECT COUNT(*) FROM skills")
    assert rows[0][0] == 0


# --------------------------------------------------------------------------
# 唯一性换范围
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_scope_migration_swaps_unique_constraint(legacy_db):
    conn = connections.get("default")
    assert ["name"] in await _unique_indexes(conn)  # 迁移前：全局唯一

    await _migrate_skill_name_scope(legacy_db)

    uniques = await _unique_indexes(conn)
    assert ["author_id", "name"] in uniques
    assert ["name"] not in uniques
    assert await _scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE name='skills_old'") == 0


@pytest.mark.asyncio
async def test_scope_migration_keeps_children_and_their_foreign_keys(legacy_db):
    """子表既不能被删数据，也不能被改掉 REFERENCES。"""
    conn = connections.get("default")

    await _migrate_skill_name_scope(legacy_db)

    # ① 子表仍然指向 skills，而不是重建时的临时表名
    for table in ("skill_versions", "download_logs"):
        assert 'REFERENCES "skills"' in await _table_sql(conn, table)

    # ② 子表数据没被 DROP TABLE 的级联删掉
    assert await _scalar(conn, "SELECT COUNT(*) FROM skill_versions") == 1
    assert await _scalar(conn, "SELECT COUNT(*) FROM download_logs") == 1
    assert await _scalar(conn, "SELECT version FROM skill_versions") == "1.0.0"

    # ③ 老 skill 本身完整搬了过来（含补列回填的 source_type 和下载数）
    _, rows = await conn.execute_query(
        "SELECT id, name, display_name, author_id, download_count, source_type FROM skills"
    )
    assert [tuple(r) for r in rows] == [(OLD_SKILL, "old-skill", "Old", ALICE, 7, "local")]


@pytest.mark.asyncio
async def test_scope_migration_leaves_foreign_keys_on(legacy_db):
    """迁移借用外键开关，结束后必须恢复 —— 否则以后删 skill 不再级联清理。"""
    conn = connections.get("default")

    await _migrate_skill_name_scope(legacy_db)

    assert await _scalar(conn, "PRAGMA foreign_keys") == 1
    # 真的在生效：删掉 skill，子表要跟着走
    await conn.execute_query("DELETE FROM skills WHERE id = ?", [OLD_SKILL])
    assert await _scalar(conn, "SELECT COUNT(*) FROM skill_versions") == 0
    assert await _scalar(conn, "SELECT COUNT(*) FROM download_logs") == 0


@pytest.mark.asyncio
async def test_scope_migration_is_idempotent(legacy_db):
    conn = connections.get("default")

    await _migrate_skill_name_scope(legacy_db)
    await _migrate_skill_name_scope(legacy_db)  # 第二次应当直接返回
    await _migrate_skill_name_scope(legacy_db)

    assert await _scalar(conn, "SELECT COUNT(*) FROM skills") == 1
    assert ["author_id", "name"] in await _unique_indexes(conn)


@pytest.mark.asyncio
async def test_scope_migration_allows_same_name_across_authors(legacy_db):
    """需求的核心：不同作者可以同名，同一作者不能同名。"""
    conn = connections.get("default")
    await _migrate_skill_name_scope(legacy_db)

    await _add_skill(conn, BOB_SKILL, "old-skill", BOB)  # 别人用同样的名字：允许
    assert await _scalar(conn, "SELECT COUNT(*) FROM skills WHERE name = 'old-skill'") == 2

    with pytest.raises(IntegrityError):
        await _add_skill(conn, DUP_SKILL, "old-skill", ALICE)  # 自己重名：拒绝


@pytest.mark.asyncio
async def test_scope_migration_on_fresh_install_is_a_noop(tmp_path):
    """全新安装时表已经是新形态，迁移必须什么都不做。"""
    db_url = f"sqlite://{tmp_path / 'fresh.db'}"
    await Tortoise.init(
        db_url=db_url,
        modules={"models": ["skillhub_selfhost.auth.models", "skillhub_selfhost.skills.models"]},
    )
    try:
        await Tortoise.generate_schemas()
        conn = connections.get("default")

        await _migrate_skill_name_scope(db_url)

        assert ["author_id", "name"] in await _unique_indexes(conn)
        assert await _scalar(conn, "SELECT COUNT(*) FROM sqlite_master WHERE name='skills_old'") == 0
    finally:
        await Tortoise.close_connections()
