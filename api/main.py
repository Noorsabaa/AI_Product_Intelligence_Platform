from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import dashboard, ingest, pipeline

app = FastAPI(title="AI Complaint Intelligence Platform API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["dashboard"]
)

app.include_router(
    ingest.router,
    prefix="/ingest",
    tags=["ingest"]
)

app.include_router(
    pipeline.router,
    prefix="/pipeline",
    tags=["pipeline"]
)

@app.get("/health")
def health():
    return {"status": "ok"}