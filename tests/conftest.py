import pytest
import tempfile
from pathlib import Path
from tortoise import Tortoise

@pytest.fixture(autouse=True)
async def setup_db():
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": [
            "skillhub_selfhost.auth.models",
            "skillhub_selfhost.skills.models",
        ]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()


@pytest.fixture
def skills_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)