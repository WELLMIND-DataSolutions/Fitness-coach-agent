"""FastAPI application entrypoint."""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.config import get_settings
from app.deps import limiter
from app.logging_setup import configure_logging
from app.routers import auth, chat, health, notifications
from app.worker import start_in_background

configure_logging()
settings = get_settings()
log = logging.getLogger("fitcoach.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    stop_worker = start_in_background() if settings.run_reminder_worker_in_api else None
    yield
    if stop_worker:
        stop_worker.set()


app = FastAPI(
    lifespan=lifespan,
    title="FitCoach API",
    version="1.0.0",
    # Interactive docs are handy locally but should not be public in production.
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None,
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    log.info(
        "%s %s %s %.0fms id=%s",
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - start) * 1000,
        request_id,
    )
    return response


@app.exception_handler(RateLimitExceeded)
async def rate_limited(_request: Request, _exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Too many requests. Wait a minute and try again."})


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Try again."})


app.include_router(health.router)
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(notifications.router)