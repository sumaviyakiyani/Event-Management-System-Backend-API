"""Test setup: an isolated PostgreSQL test database, recreated for every test."""
import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv

load_dotenv()

_test_url = os.getenv("TEST_DATABASE_URL")
_real_url = os.getenv("DATABASE_URL")
if not _test_url:
    pytest.exit("Set TEST_DATABASE_URL in .env (a separate database for tests).", returncode=2)
# Safety: tests drop all tables, so never allow them to touch the real database.
if _test_url == _real_url or "test" not in _test_url.rsplit("/", 1)[-1].lower():
    pytest.exit("TEST_DATABASE_URL must be a different database whose name contains 'test'.", returncode=2)

os.environ["DATABASE_URL"] = _test_url
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-key-with-at-least-32-chars")

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402

import app.models  # noqa: E402,F401
from app.db import Base, get_db, to_async_url  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    """HTTP client wired to the app, with fresh empty tables for each test."""
    engine = create_async_engine(to_async_url(_test_url), poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as c:
        yield c
    fastapi_app.dependency_overrides.clear()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def auth_headers(client):
    """Register + log in a user and return the Authorization header."""
    await client.post(
        "/auth/register",
        json={"username": "tester", "email": "tester@example.com", "password": "Secret123!"},
    )
    resp = await client.post("/auth/login", data={"username": "tester", "password": "Secret123!"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}
