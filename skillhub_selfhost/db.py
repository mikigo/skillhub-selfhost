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

async def close_db():
    await Tortoise.close_connections()