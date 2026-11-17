"""FastAPI application entry point."""
import logging
import socket
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError

from app import db
from app.routers import events, registrations, users

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """On startup: verify PostgreSQL is reachable, then create missing tables."""
    try:
        await db.check_connection()
        await db.init_models()
    except Exception as exc:
        logger.error("Cannot connect to PostgreSQL. Check DATABASE_URL in .env and that the server is running.")
        raise RuntimeError(f"Database connection failed: {exc}") from exc
    logger.info("Database connection OK, tables ready.")
    yield
    await db.engine.dispose()


app = FastAPI(
    title="Corporate Event Management API",
    description="Create corporate events and register employees. "
    "Use **Authorize** (top right) after logging in via `/auth/login` to call protected routes.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(users.router)
app.include_router(events.router)
app.include_router(registrations.router)


@app.exception_handler(OperationalError)
@app.exception_handler(InterfaceError)
@app.exception_handler(ConnectionError)
@app.exception_handler(socket.gaierror)
async def database_unavailable(_: Request, __: Exception):
    """Turn database connection failures into a clean 503 instead of a crash."""
    return JSONResponse(status_code=503, content={"detail": "Database is unavailable"})


@app.get("/health", tags=["Health"], summary="Check that the API and database are working")
async def health():
    await db.check_connection()
    return {"status": "ok", "database": "connected"}
