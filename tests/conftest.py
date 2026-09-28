import pytest
from tortoise.contrib.test import initializer, finalizer

@pytest.fixture(autouse=True)
def setup_db():
    initializer(
        ["skillhub_selfhost.auth.models", "skillhub_selfhost.skills.models"],
        db_url="sqlite://:memory:",
    )
    yield
    finalizer()