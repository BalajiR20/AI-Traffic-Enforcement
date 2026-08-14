"""
FastAPI application entry point.

Run from the project root:
    uvicorn backend.main:app --reload --port 8000

Docs available at http://127.0.0.1:8000/docs
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import engine, Base
from backend.routes import violations, blacklist, analytics

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI Traffic Violation Detection & Enforcement API",
    version="1.0.0",
)

# Allow the dashboard (served separately, e.g. via a static file server) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(violations.router)
app.include_router(blacklist.router)
app.include_router(analytics.router)

# Serve evidence images directly so the dashboard can <img src="/evidence/..."> them
EVIDENCE_DIR = Path(__file__).resolve().parents[1] / "evidence" / "images"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(EVIDENCE_DIR)), name="evidence")


@app.get("/")
def root():
    return {"status": "ok", "service": "traffic-violation-backend"}
