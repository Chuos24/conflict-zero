#!/usr/bin/env python3
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API startup")
    try:
        from app.migration import apply_migration
        await apply_migration()
        logger.info("ê Database migration completed")
    except ImportError:
        logger.warning("Migration module not found, skipping")
    except Exception as e:
        logger.warning(f"Migration error: {e}")
    yield
    logger.info("API shutdown")

app = FastAPI(
    title="ConflictZero API",
    description="Corporate conflict-of-interest verification",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "ConflictZero API v4.0.0", "status": "operational", "docs": "/docs"}

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "version": "4.0.0", "service": "ConflictZero"}

try:
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
    logger.info("Auth router loaded")
except Exception as e:
    logger.error(f"Auth router error: {e}")

try:
    from app.routers.verification import router as verification_router
    app.include_router(verification_router, prefix="/api/v1", tags=["verification"])
    logger.info("Verification router loaded")
except Exception as e:
    logger.error(f"Verification router error: {e}")

try:
    from app.routers.consulta import router as consulta_router
    app.include_router(consulta_router, prefix="/api/v1", tags=["consulta"])
    logger.info("Consulta router loaded")
except Exception as e:
    logger.error(f"Consulta router error: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
