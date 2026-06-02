# Conflict Zero API - Main Application
# DEPLOY_TIMESTAMP: 2026-04-09-06-39
# Last updated: 2026-04-08 17:30 UTC - Fixed UserProfileUpdate import
# Trigger force redeploy     
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
from collections import defaultdict
from datetime import datetime, timedelta
from app.core.config import get_settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models import User
from app.routers import auth_router, verification_router, dashboard_router, health_router, consulta_router, debug_router, compare_router, payments_router, admin_router, notifications_router, network_router, invitations_router, certificates_router, features_router
from app.routers.tags import router as tags_router
from app.routers.templates import router as templates_router
from app.routers.payments_v2 import router as payments_v2_router
import uuid
from app.core.rate_limit import RateLimitHeadersMiddleware

settings = get_settings()

app = FastAPI(
    title="Conflict Zero API",
    description="Sistema de Verificación de Integridad Empresarial para Perú",
    version="3.0.1",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitHeadersMiddleware)

@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.email == "admin@conflictzero.com").first()
        if not admin:
            admin_user = User(
                id=str(uuid.uuid4()),
                email="admin@conflictzero.com",
                hashed_password=get_password_hash("admin2026"),
                full_name="Administrador",
                ruc="20999999999",
                company_name="Conflict Zero Admin",
                is_admin=True,
                is_active=True,
                plan_type="enterprise",
                monthly_limit=100000
            )
            db.add(admin_user)
            db.commit()
    finally:
        db.close()

@app.get("/")
async def root():
    return {
        "name": "Conflict Zero API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health": "/health",
        "status": "/status"
    }

# API v1 routers (existing)
app.include_router(health_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(consulta_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(payments_v2_router, prefix="/api/v1")
app.include_router(invitations_router, prefix="/api/v1")
app.include_router(certificates_router, prefix="/api/v3")
app.include_router(features_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(network_router, prefix="/api/v1")

# API v3 routers (new features)
app.include_router(tags_router, prefix="/api/v3")
app.include_router(templates_router, prefix="/api/v3")# Render rebuild force - Tue May 26 15:49:54 CEST 2026

# Force redeploy Tue Jun  2 13:30:56 UTC 2026
