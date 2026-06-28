"""
main.py — FastAPI Application Entry Point
Wires together routers, CORS, startup events.

On startup: Base.metadata.create_all() creates all ORM tables.
In production: use Alembic migrations instead.

Run locally: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
Run Docker:  docker-compose up
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
from app.config import settings
from app.database import engine, Base
from app.models import user, commitment, task, reminder, channel, daily_highlight
from app.focus import models as focus_models

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI Productivity Assistant API...")
    Base.metadata.create_all(bind=engine)
    logger.success(f"DB tables ready. ENV={settings.APP_ENV}")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="AI Productivity Assistant API",
    description="LLM-powered commitment management with NVIDIA NIM + Supabase",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routers.auth import router as auth_router
from app.routers.commitments import router as commitments_router
from app.routers.tasks import router as tasks_router
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
app.include_router(focus_router)
app.include_router(reminders_router)
app.include_router(analytics_router)
app.include_router(ai_router)
app.include_router(channels_router)
app.include_router(rituals_router)
app.include_router(calendar_router)

@app.get("/")
def root():
    return {"message": "AI Productivity Assistant API", "docs": "/docs", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok", "env": settings.APP_ENV}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})
