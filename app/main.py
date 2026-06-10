#!/usr/bin/env python3
"""
ConflictZero FastAPI Application - v4.0
Production-ready with CRITICAL routers only
Minimal router loading - ONLY auth, verification, consulta
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asyncontextmanager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asyncontextmanager
async def lifespan(app: FastAPI):
    logger.info("[STARTUP] ConflictZero API v4.0 - CRITICAL ROUTERS ONLY")
    yield
    logger.info("[SHUTDcOUN] ConflictZero API shutdown")

app = FastAPI(
    title="ConflictZero API",
    description="Corporate conflict-of-interest and supplier risk verification",
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
    return {'message': 'ConflictZero API v4.0.0', 'status': 'operational', 'docs': '/docs', 'health': '/api/v1/health'}

@app.get("/api/v1/health")
async def health_check():
    return {'status': 'healthy', 'version': '4.0.0', 'service': 'ConflictZero API'}

# Auth Router (CRITICAL)
try:
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
    logger.info("[ROUTEQS $ýAuth router loaded successfully")
except ImportError as e:
    logger.error(f"[ERROR!tuth router failed to import: {e}")
except Exception as e:
    logger.error(f"[ERROR] Error loading auth router: {e}")

# Verification Router (CORE FEATURE)
try:
    from app.routers.verification import router as verification_router
    app.include_router(verification_router, prefix="/api/v1", tags=["verification"])
    logger.info("[ROUTEQS $ýVerification router loaded successfully")
except ImportError as e:
    logger.error(f"[ERRORC¥VerOdÃGM'router failed to import: {e}")
except Exception as e:
    logger.error(f"[ERRORC	EXcrsror loading verification router: {e}")

# Consulta Router (RUC lookups)
try:
    from app.routers.consulta import router as consulta_router
    app.include_router(consulta_router, prefix="/api/v1", tags=["consulta"])
    logger.info("[ROUTEQS $ýConsulta router loaded successfully")
except ImportError as e:
    logger.error(f"[ERROR] Consulta router failed to import: {e}")
except Exception as e:
    logger.error(f"[ERROR] Error loading consulta router: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)