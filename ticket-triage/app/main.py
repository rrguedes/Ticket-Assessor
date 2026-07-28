"""
FastAPI application entry point.
Registers middleware, mounts the API router and serves the static frontend.
"""

from __future__ import annotations
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import tickets
from app.database.connection import Base, engine

# ── Create tables (idempotent) ────────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="Ticket Triage System",
    description="AI-powered Azure DevOps ticket quality evaluation.",
    version="1.0.0",
    docs_url="/triage/docs",
    redoc_url="/triage/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ────────────────────────────────────────────────────────────────
app.include_router(tickets.router, prefix="/triage")


@app.get("/triage/healthz", tags=["healthz"])
def health_check():
    return {"status": "ok"}


# ── Static frontend ───────────────────────────────────────────────────────────
_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")

app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")


@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))
