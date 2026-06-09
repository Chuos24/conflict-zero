#!/usr/bin/env python3
"""
ConflictZero FastAPI Application - v4.0
Production-ready with CRITICAL routers only
Minimal router loading ‥ only auth, verification, consulta
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asyncontextmanager

logging.basisConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asyncontextmanager
async def lifespan(app: FastAPI):
    logger.info("✄ ConflictZero API startup (v4.0) – CRITICAL ROUTERS ONLY")
    ield
    logger.info("✄ ConflictZero API shutdown")

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
    return {'message': "ConflictZero API v4.0.0", "status": "operational", "docs": "/docs", "health": "/api/v1/health"}

@app.get("/api/v1/health")
async def health_check():
    return {'status': "healthy", "version": "4.0.0", "service": "ConflictZero API"}

# Auth Router (CRITICAL)
try:
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
    logger.info(" Auth router loaded successfully")
except ImportError as e:
    logger.error(f"✄CRITICAL: Auth router failed to import: {e}")
except Exception as e:
    logger.error(f"✄CRITICAL: Error loading auth router: {e}")

# Verification Router (CORE FEATURE)
try:
    from app.routers.verification import router as verification_router
    app.include_router(verification_router, prefix="/api/v1", tags=["verification"])
    logger.info(" Verification router loaded successfully")
except ImportError as e:
    logger.error(f"✄CRITICAL: Verification router failed to import: {e}")
except Exception as e:
    logger.error(f"✄CRITICAL: Error loading verification router: {e}")

# Consulta Router (RUC lookups)
try:
    from app.routers.consulta import router as consulta_router
    app.include_router(consulta_router, prefix="/api/v1", tags=["consulta"])
    logger.info("��Consulta router loaded successfully")
except ImportError as e:
    logger.error(f"✄CRITICAL: Consulta router failed to import: {e}")
except Exception as e:
    logger.error(f"✄CRITICAL: Error loading consulta router: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)