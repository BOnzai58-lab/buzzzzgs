from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from app.core.config import settings
from app.core.database import create_all_tables as create_tables
from app.auth.router import router as auth_router
from app.api.programs import router as programs_router
from app.api.scans import router as scans_router
from app.api.data import router as data_router
from app.api.findings import router as findings_router
from app.api.reports import router as reports_router
from app.api.tools import router as tools_router
from app.api.approvals import router as approvals_router
from app.api.batches import router as batches_router
from app.api.jobs import router as jobs_router
from app.api.schedules import router as schedules_router
from app.api.workers import router as workers_router
from app.api.authorizations import router as authorizations_router
from app.api.policies import router as policies_router

app = FastAPI(
    title="BugHunter AI",
    description="AI-powered bug bounty reconnaissance and vulnerability analysis platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(auth_router, prefix=PREFIX)
app.include_router(programs_router, prefix=PREFIX)
app.include_router(scans_router, prefix=PREFIX)
app.include_router(data_router, prefix=PREFIX)
app.include_router(findings_router, prefix=PREFIX)
app.include_router(reports_router, prefix=PREFIX)
app.include_router(tools_router, prefix=PREFIX)
app.include_router(approvals_router, prefix=PREFIX)
app.include_router(batches_router, prefix=PREFIX)
app.include_router(jobs_router, prefix=PREFIX)
app.include_router(schedules_router, prefix=PREFIX)
app.include_router(workers_router, prefix=PREFIX)
app.include_router(authorizations_router, prefix=PREFIX)
app.include_router(policies_router, prefix=PREFIX)


@app.on_event("startup")
async def startup():
    logger.info("Starting BugHunter AI backend...")
    try:
        await create_tables()
    except Exception as exc:
        logger.warning(f"Database table verification encountered an issue (non-fatal): {exc}")
    logger.info(f"AI proxy: {settings.AI_BASE_URL} model: {settings.AI_MODEL}")
    logger.info("Backend ready.")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"error": {"code": 500, "message": "Internal server error"}})

