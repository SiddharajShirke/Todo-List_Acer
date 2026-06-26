"""
database.py — Dual Database Layer
SQLAlchemy ORM for all CRUD (connects to Supabase Postgres or SQLite for dev).
Supabase client for auth/realtime/storage (lazy-initialized).

For local dev without Supabase, DATABASE_URL defaults to sqlite:///./dev.db
"""
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from loguru import logger
from app.config import settings

is_sqlite = settings.DATABASE_URL.startswith("sqlite")
engine_kwargs = {"echo": settings.APP_ENV == "development"}
if not is_sqlite:
    engine_kwargs.update({"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20, "pool_recycle": 1800})

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

if is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    """All ORM models inherit from this."""
    pass

def get_db():
    """FastAPI dependency — yields DB session, always closes."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error(f"DB session error: {e}")
        raise
    finally:
        db.close()

supabase_client = None

def get_supabase_client():
    """Lazy-init Supabase client (service role — bypasses RLS)."""
    global supabase_client
    if supabase_client is None and settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY:
        try:
            from supabase import create_client
            supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.warning(f"Supabase client init failed: {e}")
    return supabase_client
