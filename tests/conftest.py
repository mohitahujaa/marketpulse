"""
Pytest configuration with async support and test DB setup.
Uses an in-memory SQLite for fast, isolated tests — no real DB needed.
"""
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User, UserRole

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_db():
    """Create fresh tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    """Provide a test DB session with override."""
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """HTTP client with DB dependency overridden to use test session."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def regular_user(db_session: AsyncSession) -> User:
    """Create and persist a standard user for use in tests."""
    user = User(
        email="user@test.com",
        username="testuser",
        hashed_password=hash_password("Password1"),
        role=UserRole.USER,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create and persist an admin user for use in tests."""
    user = User(
        email="admin@test.com",
        username="adminuser",
        hashed_password=hash_password("Password1"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_token(client: AsyncClient) -> str:
    """Register and login a user, returning their access token."""
    await client.post("/api/v1/auth/register", json={
        "email": "user@test.com",
        "username": "testuser",
        "password": "Password1",
    })
    response = await client.post("/api/v1/auth/login", json={
        "email": "user@test.com",
        "password": "Password1",
    })
    return response.json()["data"]["access_token"]


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """Login as admin, returning access token."""
    from app.core.security import create_access_token
    return create_access_token(subject=str(admin_user.id), role="admin")
