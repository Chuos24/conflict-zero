#!/usr/bin/env python3
"""
ConflictZero FastAPI Application - v3.0
Production-ready with core routers
Progressive router loading with error handling
"""

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("✅ ConflictZero API startup (v3.0)")
    yield
    logger.info("✅ ConflictZero API shutdown")

# Create FastAPI app
app = FastAPI(
    title="ConflictZero API",
    description="Corporate conflict-of-interest and supplier risk verification",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Trust proxy headers
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoints
@app.get("/")
async def root():
    return {
        "message": "ConflictZero API v3.0.0",
        "status": "operational",
        "docs": "/docs",
        "health": "/api/v1/health"
    }

@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "service": "ConflictZero API"
    }

# ────────────────────────────────────────────────────────────────────────────
# ROUTER LOADING — Try-except wrapped for robustness
# ────────────────────────────────────────────────────────────────────────────

# Health Router
try:
    from app.routers.health import router as health_router
    app.include_router(health_router, prefix="/api/v1", tags=["health"])
    logger.info("✅ Health router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Health router unavailable: {e}")
except Exception as e:
    logger.error(f"❌ Error loading health router: {e}")

# Auth Router (CRITICAL)
try:
    from app.routers.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1", tags=["auth"])
    logger.info("✅ Auth router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Auth router unavailable: {e}")
except Exception as e:
    logger.error(f"❌ Error loading auth router: {e}")

# Verification Router (CORE)
try:
    from app.routers.verification import router as verification_router
    app.include_router(verification_router, prefix="/api/v1", tags=["verification"])
    logger.info("✅ Verification router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Verification router unavailable: {e}")
except Exception as e:
    logger.error(f"❌ Error loading verification router: {e}")

# Consulta Router (RUC lookups)
try:
    from app.routers.consulta import router as consulta_router
    app.include_router(consulta_router, prefix="/api/v1", tags=["consulta"])
    logger.info("✅ Consulta router loaded")
except ImportError as e:
    logger.warning(f"⚠️ Consulta router unavailable: {e}")
except Exception as e:
    logger.error(f"❌ Error loading consulta router: {e}")

# Optional routers (graceful failure)
try:
    from app.routers.dashboard import router as dashboard_router
    app.include_router(dashboard_router, prefix="/api/v1", tags=["dashboard"])
    logger.info("✅ Dashboard router loaded")
except Exception as e:
    logger.warning(f"⚠️ Dashboard router skipped: {type(e).__name__}")

try:
    from app.routers.admin import router as admin_router
    app.include_router(admin_router, prefix="/api/v1", tags=["admin"])
    logger.info("✅ Admin router loaded")
except Exception as e:
    logger.warning(f"⚠️ Admin router skipped: {type(e).__name__}")

try:
    from app.routers.tags import router as tags_router
    app.include_router(tags_router, prefix="/api/v1", tags=["tags"])
    logger.info("✅ Tags router loaded")
except Exception as e:
    logger.warning(f"⚠️ Tags router skipped: {type(e).__name__}")

# ────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
