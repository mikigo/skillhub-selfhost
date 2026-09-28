import pytest
from tortoise import Tortoise

@pytest.fixture(autouse=True)
async def setup_db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["skillhub_selfhost.auth.models"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()