# skillhub_selfhost/db.py
from tortoise import Tortoise


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


async def _migrate_add_columns(db_url: str):
    if not db_url.startswith("sqlite"):
        return
    from tortoise import connections
    conn = connections.get("default")
    try:
        await conn.execute_query("ALTER TABLE skills ADD COLUMN original_author VARCHAR(128)")
    except Exception:
        pass
    try:
        await conn.execute_query("ALTER TABLE skills ADD COLUMN source_url VARCHAR(1024)")
    except Exception:
        pass


async def close_db():
    await Tortoise.close_connections()