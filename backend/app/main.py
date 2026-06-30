"""
main.py — FastAPI Application Entry Point

Startup sequence:
  1. Verify DB connection (fail fast if Supabase unreachable)
  2. Create all ORM tables (idempotent — safe to run every startup)
  3. Mount all routers

Run locally: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Run Docker:  docker-compose up
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import asyncio
import sys

# Fix for psycopg3 on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.config import settings
from app.database import engine, Base, verify_db_connection
from redis import asyncio as aioredis
import os
import os

# Import all models to ensure they are registered with Base before create_all
from app.models import (
    user, commitment, channel, weekly_plan, daily_plan,
    task, daily_highlight, reminder
)
from app.focus import models as focus_models


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Starting AI Productivity Assistant API...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   Database: {'PostgreSQL (Supabase)' if settings.is_postgres else 'SQLite (dev fallback)'}")

    # Verify DB is reachable before accepting traffic
    if not verify_db_connection():
        logger.critical("❌ Database connection failed — check DATABASE_URL in .env")
    else:
        # Create all tables (idempotent, won't drop existing data)
        Base.metadata.create_all(bind=engine)
        logger.success("✅ DB tables ready")

    # ── Redis Connection Initialization ────────────────────────────────────────
    if settings.REDIS_URL:
        try:
            redis_client = aioredis.from_url(settings.REDIS_URL, encoding="utf8", decode_responses=False)
            app.state.redis = redis_client
            logger.success("✅ Redis connection pool ready (Basic key-value usage)")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}")
    else:
        logger.warning("⚠️ REDIS_URL not set.")

    # ── LangGraph Checkpointer + Graph Initialization ──────────────────────
    app.state.graph = None
    app.state.checkpointer = None
    if settings.ASYNC_DATABASE_URL:
        try:
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            from app.ai.graph.graph import build_graph

            async with AsyncPostgresSaver.from_conn_string(
                settings.ASYNC_DATABASE_URL
            ) as checkpointer:
                await checkpointer.setup()   # idempotent — creates checkpoint tables if needed
                app.state.checkpointer = checkpointer
                app.state.graph = build_graph(checkpointer=checkpointer)
                logger.success("✅ LangGraph graph + PostgresSaver checkpointer ready")

                yield   # ← App serves traffic here (checkpointer context stays alive)

        except Exception as e:
            logger.error(f"❌ LangGraph initialization failed: {e}")
            logger.warning("   AI chat endpoints will return 503 until this is resolved.")
            yield   # Still serve non-AI endpoints
    else:
        logger.warning("⚠️ ASYNC_DATABASE_URL not set — LangGraph graph NOT initialized. AI chat disabled.")
        yield

    logger.info("Shutting down AI Productivity Assistant API...")


app = FastAPI(
    title="AI Productivity Assistant API",
    description="LLM-powered productivity management with Supabase + Google OAuth",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────────
from app.routers.auth import router as auth_router
from app.routers.commitments import router as commitments_router
from app.routers.tasks import router as tasks_router
from app.routers.daily_plans import router as daily_plans_router
from app.routers.weekly_plans import router as weekly_plans_router
from app.focus.router import router as focus_router
from app.routers.reminders import router as reminders_router
from app.routers.analytics import router as analytics_router
from app.routers.ai import router as ai_router
from app.routers.channels import router as channels_router
from app.routers.rituals import router as rituals_router
from app.routers.calendar import router as calendar_router

app.include_router(auth_router)
app.include_router(commitments_router)
app.include_router(tasks_router)
app.include_router(daily_plans_router)
app.include_router(weekly_plans_router)   # Includes /api/weekly-plans AND /api/weekly-objectives (backward compat)
app.include_router(focus_router)
app.include_router(reminders_router)
app.include_router(analytics_router)
app.include_router(ai_router)
app.include_router(channels_router)
app.include_router(rituals_router)
app.include_router(calendar_router)


# ── Health Endpoints ───────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "message": "AI Productivity Assistant API v2.0",
        "docs": "/docs",
        "version": "2.0.0",
        "database": "Supabase PostgreSQL" if settings.is_postgres else "SQLite (dev)"
    }


@app.get("/health")
def health(request: Request):
    db_ok = verify_db_connection()
    graph_ok = getattr(request.app.state, "graph", None) is not None
    return {
        "status": "ok" if db_ok else "degraded",
        "env": settings.APP_ENV,
        "database": "connected" if db_ok else "error",
        "graph": "initialized" if graph_ok else "not_initialized",
        "supabase_configured": bool(settings.SUPABASE_URL and settings.SUPABASE_SERVICE_ROLE_KEY),
    }


# ── Global Error Handler ───────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
