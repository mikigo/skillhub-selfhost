# skillhub_selfhost/db.py
from __future__ import annotations

import logging
from tortoise import Tortoise

logger = logging.getLogger(__name__)

# 建表之后补齐的列。generate_schemas() 只发 CREATE TABLE IF NOT EXISTS，
# 不会给已存在的表加列，所以每次启动都要在这里幂等地补一遍。
_SKILL_COLUMNS = [
    ("original_author", "VARCHAR(128)", "VARCHAR(128)"),
    ("source_url", "VARCHAR(1024)", "VARCHAR(1024)"),
    ("source_type", "VARCHAR(16) DEFAULT 'local'", "VARCHAR(16) DEFAULT 'local'"),
    ("source_branch", "VARCHAR(255)", "VARCHAR(255)"),
    ("source_path", "VARCHAR(1024)", "VARCHAR(1024)"),
]


async def init_db(db_url: str):
    await Tortoise.init(
        db_url=db_url,
        modules={
            "models": [
                "skillhub_selfhost.auth.models",
                "skillhub_selfhost.skills.models",
            ]
        },
    )
    await Tortoise.generate_schemas()
    await _migrate_add_columns(db_url)
    await _migrate_skill_name_scope(db_url)


async def _migrate_add_columns(db_url: str):
    from tortoise import connections
    conn = connections.get("default")

    if db_url.startswith("sqlite"):
        # SQLite 没有 ADD COLUMN IF NOT EXISTS，靠重复执行报错来实现幂等
        for name, sqlite_type, _ in _SKILL_COLUMNS:
            try:
                await conn.execute_query(f"ALTER TABLE skills ADD COLUMN {name} {sqlite_type}")
            except Exception:
                pass
    elif db_url.startswith("postgres"):
        # 这里不吞异常：真正的失败应该在启动时就暴露，而不是变成以后的 500
        for name, _, pg_type in _SKILL_COLUMNS:
            await conn.execute_query(f"ALTER TABLE skills ADD COLUMN IF NOT EXISTS {name} {pg_type}")
    else:
        logger.warning("不支持的数据库方言，跳过 skills 表补列：%s", db_url)
        return

    # 存量行没有 source_type，回填为 local
    try:
        await conn.execute_query("UPDATE skills SET source_type = 'local' WHERE source_type IS NULL")
    except Exception:
        pass


async def _sqlite_skill_scope_is_author_scoped(conn) -> bool:
    """是否已经存在「唯一且恰好覆盖 (author_id, name)」的索引。

    不去比对建表语句文本，只看索引的实际形状 —— 这样不依赖 Tortoise 生成 DDL 的写法。
    """
    _, indexes = await conn.execute_query("PRAGMA index_list('skills')")
    for row in indexes:
        index_name, is_unique = row[1], row[2]
        if not is_unique:
            continue
        _, columns = await conn.execute_query(f"PRAGMA index_info('{index_name}')")
        if [c[2] for c in columns] == ["author_id", "name"]:
            return True
    return False


async def _table_columns(conn, table: str) -> list[str]:
    _, rows = await conn.execute_query(f"PRAGMA table_info('{table}')")
    return [r[1] for r in rows]


async def _commit_quietly(conn):
    """结束当前隐式事务。没有事务在跑时 COMMIT 会报错，忽略即可。"""
    try:
        await conn.execute_query("COMMIT")
    except Exception:
        pass


async def _foreign_keys_enabled(conn) -> bool:
    _, rows = await conn.execute_query("PRAGMA foreign_keys")
    return bool(rows and rows[0][0])


async def _set_foreign_keys(conn, on: bool):
    """切外键开关，并断言真的切过去了。

    PRAGMA foreign_keys 在事务里是空操作，静默失败会引发很隐蔽的坏数据，所以这里
    读回来确认。注意 aiosqlite 的隐式事务是 DML 触发的，调用前务必先 _commit_quietly。
    """
    await _commit_quietly(conn)
    await conn.execute_query(f"PRAGMA foreign_keys={'ON' if on else 'OFF'}")
    if await _foreign_keys_enabled(conn) != on:
        raise RuntimeError(f"无法把 SQLite 外键切到 {'ON' if on else 'OFF'}，中止 skills 表重建")


async def _migrate_skill_name_scope(db_url: str):
    """把 skills 的唯一性从「全局 name」改成「(author_id, name)」。

    SQLite 的 name 唯一性是 CREATE TABLE 里的内联 UNIQUE，没有 DROP CONSTRAINT 可用，
    只能整表重建。Postgres 是普通约束，删掉再建索引即可。
    """
    from tortoise import connections
    conn = connections.get("default")

    if db_url.startswith("sqlite"):
        if await _sqlite_skill_scope_is_author_scoped(conn):
            return
        # 先结束 _migrate_add_columns 的 UPDATE 留下的隐式事务：事务里改了外键开关也是
        # 空操作，而且重建必须在自动提交下跑，否则关连接时会连同数据一起回滚。
        await _commit_quietly(conn)
        # 子表的 REFERENCES "skills" 都是 ON DELETE CASCADE，DROP TABLE 的隐式 DELETE
        # 会顺着级联把子表数据删光，所以外键必须先关掉（Tortoise 默认是开着的）。
        fk_was_on = await _foreign_keys_enabled(conn)
        if fk_was_on:
            await _set_foreign_keys(conn, on=False)
        try:
            # 全程不碰子表，所以不能用 ALTER TABLE ... RENAME：RENAME 会把 skill_versions /
            # download_logs 的 REFERENCES 改写成指向新名字，子表当场指空。
            # 上一次迁移中途失败可能留下残骸，先清掉，让重建可重入
            await conn.execute_query("DROP TABLE IF EXISTS skills_old")
            await conn.execute_query("CREATE TABLE skills_old AS SELECT * FROM skills")
            await conn.execute_query("DROP TABLE skills")
            await Tortoise.generate_schemas()  # skills 已不存在，这里按新模型重建
            old_cols = await _table_columns(conn, "skills_old")
            new_cols = await _table_columns(conn, "skills")
            shared = ", ".join(f'"{c}"' for c in new_cols if c in old_cols)
            await conn.execute_query(f"INSERT INTO skills ({shared}) SELECT {shared} FROM skills_old")
            await conn.execute_query("DROP TABLE skills_old")
        finally:
            # 回填的 INSERT 还挂在事务里，落盘了才算迁移完成
            await _commit_quietly(conn)
            if fk_was_on:
                await _set_foreign_keys(conn, on=True)
        logger.info("skills 唯一性已迁移为 (author_id, name)")
        return

    if db_url.startswith("postgres"):
        # (author_id, name) 是我们唯一想要的唯一约束，所以把现存的唯一约束全删掉再建
        _, rows = await conn.execute_query(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'skills'::regclass AND contype = 'u'"
        )
        for (constraint_name,) in rows:
            await conn.execute_query(f'ALTER TABLE skills DROP CONSTRAINT "{constraint_name}"')
        await conn.execute_query(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_skills_author_name ON skills (author_id, name)"
        )
        return

    logger.warning("不支持的数据库方言，跳过 skills 唯一性迁移：%s", db_url)


async def close_db():
    await Tortoise.close_connections()