"""
database.py — Production-Grade Database Layer

Architecture:
  - SQLAlchemy ORM: All CRUD operations through PostgreSQL (Supabase)
  - Supabase Python client: Auth verification + Realtime subscriptions
  - Connection Pool: psycopg2 with PgBouncer (Transaction Pooler, port 6543)

Pool strategy:
  - pool_size=20: persistent connections kept alive (increased for agent workloads)
  - max_overflow=30: burst capacity (total max 50 connections)
  - pool_recycle=1800: recycle connections every 30 min to avoid stale
  - pool_pre_ping=True: test connection health before use
  - pool_use_lifo=True: reuse the most recently used connection for lower latency
  - pool_timeout=15: wait max 15s for available connection
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import NullPool
from loguru import logger
from app.config import settings


def _build_engine():
    """Build the SQLAlchemy engine based on configured DATABASE_URL."""
    url = settings.DATABASE_URL
    is_sqlite = url.startswith("sqlite")

    if is_sqlite:
        # Legacy fallback only — should not be used in production
        logger.warning("Using SQLite — this is a development fallback. Set DATABASE_URL to Supabase Postgres.")
        eng = create_engine(url, echo=(settings.APP_ENV == "development"))

        @event.listens_for(eng, "connect")
        def set_sqlite_pragma(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()

        return eng

    # PostgreSQL (Supabase Transaction Pooler)
    # NullPool is used when behind PgBouncer in transaction mode (port 6543)
    # because PgBouncer manages the actual pool externally.
    # When using a direct connection (port 5432), use QueuePool instead.
    logger.info(f"Connecting to PostgreSQL pool (size={settings.DB_POOL_SIZE}, max_overflow={settings.DB_MAX_OVERFLOW})")

    pool_kwargs = {
        "pool_pre_ping": True,
        "pool_use_lifo": True, # Optimization: Reuse hottest connection
        "pool_size": getattr(settings, 'DB_POOL_SIZE', 20),
        "max_overflow": getattr(settings, 'DB_MAX_OVERFLOW', 30),
        "pool_timeout": getattr(settings, 'DB_POOL_TIMEOUT', 15),
        "pool_recycle": getattr(settings, 'DB_POOL_RECYCLE', 1800),
        "echo": settings.APP_ENV == "development",
    }

    # If using Supabase transaction pooler (port 6543), use NullPool
    # to avoid double-pooling issues with PgBouncer
    if ":6543/" in url:
        logger.info("Detected Transaction Pooler (port 6543) — using NullPool to avoid PgBouncer conflicts")
        engine = create_engine(url, poolclass=NullPool, echo=settings.APP_ENV == "development")
    else:
        engine = create_engine(url, **pool_kwargs)

    return engine


engine = _build_engine()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


class Base(DeclarativeBase):
    """All SQLAlchemy ORM models inherit from this base."""
    pass


def get_db():
    """
    FastAPI dependency — yields a SQLAlchemy Session.
    Rolls back on error, always closes on exit.
    Designed for use with Depends(get_db) in route handlers.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"DB session error (rolled back): {e}")
        raise
    finally:
        db.close()


def verify_db_connection() -> bool:
    """
    Test that the database connection is working.
    Called on app startup to fail fast if DB is unreachable.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.success("Database connection verified ✓")
        return True
    except Exception as e:
        logger.error(f"Database connection FAILED: {e}")
        return False


# ── Supabase Client ───────────────────────────────────────────────────────────
# Used for: Supabase Auth verification, Realtime subscriptions, Storage
# NOT used for standard CRUD (that goes through SQLAlchemy above)

_supabase_client = None


def get_supabase():
    """
    Lazy-init Supabase client using service role key.
    Service role bypasses RLS — only use on the backend, never expose to frontend.
    Returns None if Supabase is not configured.
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("Supabase client not initialized — SUPABASE_URL or SERVICE_ROLE_KEY missing in .env")
        return None

    try:
        from supabase import create_client, ClientOptions
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        logger.success("Supabase service-role client initialized ✓")
    except Exception as e:
        logger.error(f"Supabase client init failed: {e}")

    return _supabase_client


def get_supabase_anon():
    """
    Anon Supabase client — used to verify user JWTs issued by Supabase Auth.
    Safe for read-only, RLS-enforced operations.
    """
    if not settings.SUPABASE_URL or not settings.SUPABASE_ANON_KEY:
        return None
    try:
        from supabase import create_client
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    except Exception as e:
        logger.error(f"Supabase anon client init failed: {e}")
        return None
