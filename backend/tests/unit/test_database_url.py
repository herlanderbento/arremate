import pytest

from shared.infra.db.database import to_asyncpg_url


@pytest.mark.parametrize(
    "given,expected",
    [
        (
            "postgresql://u:p@ep-x.neon.tech/db?sslmode=require&channel_binding=require",
            "postgresql+asyncpg://u:p@ep-x.neon.tech/db?ssl=require",
        ),
        ("postgres://u:p@host:5432/db", "postgresql+asyncpg://u:p@host:5432/db"),
        (
            "postgresql+asyncpg://u:p@localhost:5433/db",
            "postgresql+asyncpg://u:p@localhost:5433/db",
        ),
        ("postgresql://u:p@h/db?channel_binding=require", "postgresql+asyncpg://u:p@h/db"),
        (
            "postgresql://u:p@h/db?ssl=require&sslmode=disable",
            "postgresql+asyncpg://u:p@h/db?ssl=require",
        ),
    ],
)
def test_provider_urls_work_with_asyncpg(given, expected):
    assert to_asyncpg_url(given) == expected
