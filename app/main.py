#!/usr/bin/env python3
import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from app.core.config import get_settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models import User
from app.routers import auth_router, verification_router, dashboard_router, health_router, consulta_router, debug_router, compare_router, payments_router, admin_router, notifications_router, network_router
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Conflict Zero API",
    description="Corporate conflict-of-interest verification API",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(consulta_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(network_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Conflict Zero API", "version": "3.0.0", "docs": "/docs"}

@app.get("/api/v1/health")
async def health():
    return {"status": "ok", "version": "3.0.0"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
