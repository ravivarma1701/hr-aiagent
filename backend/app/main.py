from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.logging import configure_logging
from app.db.session import SessionLocal
from app.services.ai.policy_rag import ensure_policies_ingested


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    logger = structlog.get_logger()
    try:
        async with SessionLocal() as session:
            await ensure_policies_ingested(session)
    except Exception:
        # Vector store ingestion is best-effort at startup; the Policy RAG
        # endpoint will simply report insufficient context until the
        # ingestion script is run manually if this fails (e.g. offline env
        # without the embedding model cached yet).
        logger.exception("policy_ingestion_startup_failed")
    yield


app = FastAPI(title="Mock HRMS API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api/v1")
@app.get("/health")
async def root_health():
    return {"success": True, "data": {"status": "ok"}, "error": None}
