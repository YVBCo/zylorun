from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import create_engine
from app.config import settings

raw_url = settings.DATABASE_URL or "sqlite+aiosqlite:///./test.db"

# Render & Heroku provide postgres:// URLs; modern SQLAlchemy requires postgresql://
if raw_url.startswith("postgres://"):
    raw_url = raw_url.replace("postgres://", "postgresql://", 1)

# Ensure async engine has an async driver
if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
    async_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif raw_url.startswith("sqlite://") and not raw_url.startswith("sqlite+"):
    async_url = raw_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
else:
    async_url = raw_url

# Synchronous engine helper for sync threads, background tasks, and seed operations
sync_url = raw_url.replace("+aiosqlite", "").replace("+asyncpg", "")

is_sqlite = "sqlite" in async_url
async_kwargs = {"echo": False}
sync_kwargs = {"echo": False}

if not is_sqlite:
    async_kwargs.update({
        "pool_size": 50,
        "max_overflow": 100,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })
    sync_kwargs.update({
        "pool_size": 25,
        "max_overflow": 50,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    })
else:
    async_kwargs.update({
        "pool_pre_ping": True,
    })
    sync_kwargs.update({
        "connect_args": {"check_same_thread": False, "timeout": 30},
        "pool_pre_ping": True,
    })

engine = create_async_engine(async_url, **async_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

sync_engine = create_engine(sync_url, **sync_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sync_engine)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
