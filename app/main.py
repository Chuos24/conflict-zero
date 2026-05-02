# Conflict Zero API - Main Application
# DEPLOY_TIMESTAMP: 2026-04-22-18-00-00 - Deploy test
# Last updated: 2026-04-08 17:30 UTC - Fixed UserProfileUpdate import
# FIX: CAP scoring - sanciones vigentes check
# FIX: Founder password corrected to CZ2025!
# NEW: LegalBot V3.0 - Scoring Multidimensional
# NEW: Added compare router for multi-RUC comparison

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
import time
from collections import defaultdict
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models import User
from app.routers import (auth_router, verification_router, dashboard_router, health_router, 
                         consulta_router, debug_router, compare_router, payments_router, payments_v2_router,
                         admin_router, notifications_router, network_router, certificates_router,
                         invitations_router)
import uuid

settings = get_settings()

# Initialize Sentry for error monitoring
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=os.environ.get("ENVIRONMENT", "production"),
        release=os.environ.get("RENDER_GIT_COMMIT", "unknown"),
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=0.1,  # 10% of transactions for performance monitoring
        profiles_sample_rate=0.1,
    )
    print("✅ Sentry initialized")
else:
    print("⚠️ SENTRY_DSN not set - error monitoring disabled")

print("🚀 Starting Conflict Zero API - LegalBot V3.0 - Deploy Fix")

# Crear tablas y migrar columnas faltantes (con manejo de errores para no bloquear startup)
def init_database():
    try:
        from sqlalchemy import inspect, text
        from app.models import Invitation
        
        # 1. Crear tablas que no existen
        Base.metadata.create_all(bind=engine)
        
        # 2. Migrar columnas faltantes en tablas existentes (PostgreSQL-safe)
        inspector = inspect(engine)
        
        # --- invitations table ---
        if inspector.has_table("invitations"):
            existing_cols = {c["name"] for c in inspector.get_columns("invitations")}
            required_cols = {
                "name": "VARCHAR(255)",
                "company": "VARCHAR(255)",
                "notes": "TEXT",
                "accepted_by": "VARCHAR(36)"
            }
            with engine.connect() as conn:
                for col_name, col_type in required_cols.items():
                    if col_name not in existing_cols:
                        conn.execute(text(f'ALTER TABLE invitations ADD COLUMN IF NOT EXISTS {col_name} {col_type}'))
                        conn.commit()
                        print(f"✅ Columna '{col_name}' agregada a invitations")
        
        print("✅ Base de datos lista")
        return True
    except Exception as e:
        print(f"⚠️ Error conectando a base de datos: {e}")
        return False

db_connected = init_database()

# Crear usuario founder si no existe - PASSWORD FIX APPLIED
def create_founder_user():
    if not db_connected:
        print("⚠️ Saltando creación de founder (sin conexión a DB)")
        return
    db = SessionLocal()
    try:
        # Hash pre-calculado de "CZ2025!" - bcrypt válido
        PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
        
        existing = db.query(User).filter(User.email == "founder@conflictzero.com").first()
        if existing:
            existing.hashed_password = PRECOMPUTED_HASH
            db.commit()
            print("✅ Founder hash actualizado")
            db.close()
            return
        
        founder = User(
            id=str(uuid.uuid4()),
            email="founder@conflictzero.com",
            hashed_password=PRECOMPUTED_HASH,
            full_name="Conflict Zero Founder",
            company_name="Conflict Zero Inc.",
            ruc="20100000001",
            is_active=True,
            is_admin=True
        )
        db.add(founder)
        db.commit()
        print("✅ Usuario founder creado exitosamente con contraseña CZ2025!")
    except Exception as e:
        print(f"⚠️ Error creando founder: {e}")
    finally:
        db.close()


create_founder_user()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="API de verificación predictiva de riesgo contractual para el mercado peruano",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware de logging
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Rate limiting simple (en memoria) - 100 requests por minuto por IP
request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Ignorar health checks y docs
    if request.url.path in ["/api/v1/health", "/api/v3/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    
    client_ip = request.client.host
    now = datetime.now()
    
    # Limpiar requests antiguos (> 1 minuto)
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < timedelta(minutes=1)]
    
    # Verificar límite (100 req/min)
    if len(request_counts[client_ip]) >= 100:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded", "retry_after": 60}
        )
    
    request_counts[client_ip].append(now)
    return await call_next(request)

# Routers
app.include_router(health_router, prefix="/api/v1")
app.include_router(debug_router, prefix="/api/v1")
app.include_router(consulta_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(compare_router, prefix="/api/v1")
app.include_router(payments_router, prefix="/api/v1")
app.include_router(payments_v2_router, prefix="/api/v1")
app.include_router(certificates_router, prefix="/api/v1")

# NEW: Phase 1 Migration routers
app.include_router(invitations_router, prefix="/api/v1")

# Routers v3 (para compatibilidad con frontend)
app.include_router(auth_router, prefix="/api/v3")
app.include_router(verification_router, prefix="/api/v3")
app.include_router(consulta_router, prefix="/api/v3")  # FIX: Agregado para consulta RUC
app.include_router(dashboard_router, prefix="/api/v3")  # FIX: Dashboard disponible en v3
app.include_router(compare_router, prefix="/api/v3")  # FIX: Compare disponible en v3
app.include_router(payments_router, prefix="/api/v3")  # FIX: Payments disponible en v3
app.include_router(payments_v2_router, prefix="/api/v3")  # FIX: Payments v2 disponible en v3
app.include_router(admin_router, prefix="/api/v3")
app.include_router(notifications_router, prefix="/api/v3")

# NEW: Phase 1 Migration routers v3
app.include_router(invitations_router, prefix="/api/v3")
app.include_router(network_router, prefix="/api/v3")
app.include_router(certificates_router, prefix="/api/v3")
app.include_router(health_router, prefix="/api/v3")  # FIX: Health disponible en v3

# Endpoint register-web directo (workaround para problema de caché en Render)
from pydantic import BaseModel
from typing import Optional

class RegisterWebRequest(BaseModel):
    email: str
    password: str
    full_name: str
    company_name: Optional[str] = None
    ruc: Optional[str] = None

@app.post("/api/v3/auth/register-web")
async def register_web_direct(request: RegisterWebRequest):
    """
    Registro desde formulario web - con notificaciones por email
    """
    import uuid
    import os
    import random
    import string
    import logging
    from datetime import datetime
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    from app.models import User
    from app.services.email import get_email_service
    
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    email_service = get_email_service()
    
    try:
        # Verificar si email ya existe
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            return {"success": True, "message": "Solicitud recibida"}  # No revelar si existe
        
        # Generar contraseña temporal segura
        alphabet = string.ascii_letters.replace('O', '').replace('o', '').replace('l', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
        temp_password = ''.join(random.choice(alphabet) for _ in range(12))
        
        # Crear usuario
        user = User(
            id=str(uuid.uuid4()),
            email=request.email,
            hashed_password=get_password_hash(temp_password),  # FIXED: bcrypt hash
            full_name=request.full_name,
            company_name=request.company_name or "",
            ruc=request.ruc or "00000000000",
            plan_type="professional",
            is_active=True
        )
        db.add(user)
        db.commit()
        
        # Enviar email de bienvenida al usuario
        user_email_sent = False
        try:
            user_email_sent = email_service.send_welcome_email(
                email=request.email,
                temp_password=temp_password,
                full_name=request.full_name,
                plan="professional"
            )
            if user_email_sent:
                logger.info(f"✅ Email de bienvenida enviado a {request.email}")
            else:
                logger.warning(f"⚠️ No se pudo enviar email a {request.email}. Proveedor: {email_service.provider}")
        except Exception as e:
            logger.error(f"❌ Error enviando email a usuario: {e}")
        
        # Notificar al admin sobre nuevo registro
        admin_email = "tiagomunoz10@icloud.com"
        
        admin_notifications_sent = 0
        try:
            admin_notified = email_service.send_admin_registration_notification(
                admin_email=admin_email,
                user_email=request.email,
                user_name=request.full_name,
                user_company=request.company_name or "No especificada",
                user_ruc=request.ruc or "No especificado",
                plan="professional"
            )
            if admin_notified:
                admin_notifications_sent = 1
                logger.info(f"✅ Admin notificado ({admin_email})")
            else:
                logger.warning(f"⚠️ No se pudo notificar a admin ({admin_email})")
        except Exception as e:
            logger.error(f"❌ Error notificando a admin ({admin_email}): {e}")
        
        logger.info(f"📝 Nuevo registro: {request.email} - {request.full_name}")
        
        return {
            "success": True,
            "message": "Usuario registrado exitosamente",
            "user_id": user.id,
            "email_sent": user_email_sent,
            "admin_notifications": admin_notifications_sent,
            "provider": email_service.provider
        }
    except Exception as e:
        logger.error(f"[Register Web] Error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()


# Endpoint notify-admin para notificaciones desde el frontend
@app.post("/api/v3/notify-admin")
async def notify_admin(request: dict):
    """
    Recibe notificación de nuevo registro y envía email al admin
    """
    import logging
    from datetime import datetime
    from app.services.email import get_email_service
    
    logger = logging.getLogger(__name__)
    email_service = get_email_service()
    
    try:
        ruc = request.get("ruc", "N/A")
        empresa = request.get("empresa", "No especificada")
        plan = request.get("plan", "N/A")
        email = request.get("email", "N/A")
        phone = request.get("phone", "N/A")
        nombre = request.get("nombre", "N/A")
        score = request.get("score", "N/A")
        
        admin_email = "tiagomunoz10@icloud.com"
        subject = f"🔔 Nuevo Registro - {empresa}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Inter, sans-serif; background: #0a0a0a; color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #141414; border: 1px solid #2a2a2a; border-radius: 16px; padding: 40px;">
            <h2 style="color: #c9a961; font-family: Cormorant Garamond, serif;">🚀 Nuevo Registro Conflict Zero</h2>
            <p><strong>Empresa:</strong> {empresa}</p>
            <p><strong>Contacto:</strong> {nombre}</p>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Teléfono:</strong> {phone}</p>
            <p><strong>RUC:</strong> {ruc}</p>
            <p><strong>Plan:</strong> {plan}</p>
            <p><strong>Score:</strong> {score}</p>
            <p style="color: #666; margin-top: 20px;">Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        </body>
        </html>
        """
        
        sent = email_service.send_email(admin_email, subject, html_content)
        
        if sent:
            logger.info(f"✅ Admin notificado sobre registro de {email}")
        else:
            logger.warning(f"⚠️ No se pudo notificar a admin (proveedor: {email_service.provider})")
        
        return {"success": True, "notified": sent}
    except Exception as e:
        logger.error(f"Error en notify-admin: {e}")
        return {"success": False, "error": str(e)}

# Test Sentry endpoint
@app.get("/api/v1/sentry-test")
async def sentry_test():
    """Trigger a test error for Sentry verification"""
    raise ValueError("This is a test error for Sentry - please ignore")

# Manejo de excepciones
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error": str(exc)}
    )

# Auto-migrate: crear tablas/columnas faltantes
@app.on_event("startup")
async def auto_migrate():
    """Migration: add missing columns to invitations table."""
    from app.core.database import engine
    from app.models import Base
    from sqlalchemy import text
    import logging

    logger = logging.getLogger("auto_migrate")

    # 1. Create any missing tables
    Base.metadata.create_all(bind=engine, checkfirst=True)

    # 2. Add missing columns to existing tables (PostgreSQL specific)
    with engine.connect() as conn:
        # invitations table
        conn.execute(text("""
            ALTER TABLE invitations
            ADD COLUMN IF NOT EXISTS name VARCHAR(255),
            ADD COLUMN IF NOT EXISTS company VARCHAR(255),
            ADD COLUMN IF NOT EXISTS notes TEXT,
            ADD COLUMN IF NOT EXISTS accepted_by VARCHAR(36);
        """))
        conn.commit()
        logger.info("✅ Auto-migrate: invitations columns checked")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Force redeploy trigger 2026-05-02
# Force redeploy Sat Mar 28 03:45:00 AM CST 2026 - LegalBot Universal V2.0
# LegalBot V3.0 Redeploy Sat Mar 28 03:55:04 AM CST 2026
# Redeploy Sat Mar 28 03:57:58 AM CST 2026
# Redeploy Sat Mar 28 04:05:24 AM CST 2026 - Force build
# Force deploy Sat Mar 28 04:14:44 AM CST 2026
