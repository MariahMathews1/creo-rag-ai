from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analysis_projects import router as analysis_router
from app.api.documents import router as documents_router
from app.api.manual_assistant import router as manual_router
from app.api.machine_profiles import router as machine_profiles_router
from app.api.traceability import router as traceability_router
from app.api.profile_extraction import router as profile_extraction_router
from app.core.config import get_settings
from app.db.alembic import upgrade_database
from app.db.session import engine
from app import models  # noqa: F401 - registers ORM metadata

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    upgrade_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Decision-support API for reviewing Creo NC output.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(machine_profiles_router, prefix=settings.api_prefix)
app.include_router(analysis_router, prefix=settings.api_prefix)
app.include_router(documents_router, prefix=settings.api_prefix)
app.include_router(manual_router, prefix=settings.api_prefix)
app.include_router(traceability_router, prefix=settings.api_prefix)
app.include_router(profile_extraction_router, prefix=settings.api_prefix)


@app.get("/api/health", tags=["health"])
def health_check():
    return {"status": "healthy", "service": settings.app_name}
