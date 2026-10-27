import asyncio
from pathlib import Path

import asyncpg
import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from auction.infra.ws.connection_manager import get_lot_room_notifier
from catalog.infra.api.catalog_dependencies import get_catalog_gateway
from main import app
from shared.infra.db.database import AsyncSessionLocal, engine
from shared.infra.db.metadata import target_metadata
from tests.conftest import TEST_DATABASE_URL
from tests.fakes.catalog import FakeCatalogGateway
from tests.fakes.notifier import RecordingNotifier


def _plain_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


async def _create_test_database() -> None:
    dsn = _plain_dsn(TEST_DATABASE_URL)
    db_name = dsn.rsplit("/", 1)[1].split("?")[0]
    admin = await asyncpg.connect(dsn.rsplit("/", 1)[0] + "/postgres")
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db_name)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        await admin.close()


@pytest.fixture(scope="session", autouse=True)
def _migrated_database():
    asyncio.run(_create_test_database())
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "migrations"))
    command.upgrade(config, "head")


@pytest.fixture(autouse=True)
async def _clean_tables():
    yield
    tables = ", ".join(t.name for t in target_metadata.sorted_tables)
    async with engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


def new_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def client():
    async with new_client() as c:
        yield c


@pytest.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def catalog():
    fake = FakeCatalogGateway()
    app.dependency_overrides[get_catalog_gateway] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_catalog_gateway, None)


@pytest.fixture(autouse=True)
def notifier():
    recorder = RecordingNotifier()
    app.dependency_overrides[get_lot_room_notifier] = lambda: recorder
    yield recorder
    app.dependency_overrides.pop(get_lot_room_notifier, None)
