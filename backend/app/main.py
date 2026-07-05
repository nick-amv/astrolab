"""Astrolab API application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    account,
    admin,
    assessment,
    auth,
    health,
    match,
    meta,
    occupations,
    parent,
    privacy,
    report,
)
from app.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title="Astrolab API",
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router)
    app.include_router(meta.router)
    app.include_router(privacy.router)
    app.include_router(auth.router)
    app.include_router(account.router)
    app.include_router(admin.router)
    app.include_router(occupations.router)
    app.include_router(match.router)
    app.include_router(assessment.router)
    app.include_router(report.router)
    app.include_router(parent.router)
    return app


app = create_app()
