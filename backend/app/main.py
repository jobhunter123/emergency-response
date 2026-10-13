"""Main entry point for the FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    alerts_router,
    auth_router,
    incidents_router,
    reports_router,
    users_router,
)
from app.core.config import settings
from app.db.init_db import init_db

API_V1_STR: str = settings.API_V1_STR


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan context manager for startup and shutdown events."""
    # Non-destructively ensure required database tables are initialized
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for the Emergency Response Platform prototype and decision-support system.",
    version="0.1.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Configure CORS dynamically for local and production deployment
cors_origins = [str(o).rstrip("/") for o in settings.CORS_ORIGINS]
allow_all_origins = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else cors_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers under API version prefix
app.include_router(auth_router, prefix=API_V1_STR)
app.include_router(reports_router, prefix=API_V1_STR)
app.include_router(incidents_router, prefix=API_V1_STR)
app.include_router(alerts_router, prefix=API_V1_STR)
app.include_router(users_router, prefix=API_V1_STR)

# Serve report evidence photos (configurable for local or mounted persistent disk)
upload_dir = settings.UPLOAD_DIR
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount(
    "/uploads/report_photos",
    StaticFiles(directory=str(upload_dir)),
    name="report_photos",
)


@app.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint returning service identification details."""
    return {
        "name": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Health check endpoint returning system status."""
    return {
        "status": "healthy",
    }


if __name__ == "__main__":
    import uvicorn

    server_port = int(os.environ.get("PORT", settings.PORT))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=server_port,
        reload=settings.DEBUG,
    )
