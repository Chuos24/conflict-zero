# Conflict Zero API - Main Application
# DEPLOY_TIMESTAMP: 2026-04-09-06-39-28 - Force deploy consulta
# Last updated: 2026-04-08 17:30 UTC - Fixed UserProfileUpdate import
# FIX: CAP scoring - sanciones vigentes check
# FIX: Founder password corrected to CZ2025!
# NEW: LegalBot V3.0 - Scoring Multidimensional
# NEW: Added compare router for multi-RUC comparison
# NEW: features_router - Search History + Tags + Templates

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
from app.routers.payments_v2 import router as payments_v2_router
import uuid

from app.core.rate_limit import RateLimitHeadersMiddleware

settings = get_settings()

print("🚀 Starting Conflict Zero API - LegalBot V3.0 - Deploy Fix")
print(" Rate limiting por plan activo")

# Crear tablas en la base de datos (con manejo de errores para no bloquear startup)
def init_database():
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Tablas de base de datos creadas/verificadas")
        return True
    except Exception as e:
        print(f"⚠️ Error conectando a base de datos: {e}")
        return False

db_connected = init_database()

# Crear usuario founder si no existe - PASSWORD FIRAPPLIED(ev create_founder_user():
    if not db_connected:
        print("⚠️ Saltando creación de founder (sin conexión a DB)")
        return
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "founder@conflictzero.com").first()
        if not existing:
            PRECOMPUTEDH_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
            founder = User(
                id=str(uuid.uuid4()),
                email="founder@conflictzero.com",
                hashed_password=PRECOMPUTED_HASH,
                full_name="Conflict Zero Founder",
                company_name="Conflict Zero Inc.",
                ruc="20100000001",
                is_active=True,
                is_admin=True,
                plan_type="enterprise",
                monthly_requests=0,
                monthly_limit=999999,
                api_key="cz_founder_" + str(uuid.uuid4()).replace("-", "")
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

app.add_middleware(RateLimitHeadersMiddleware)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

request_counts = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path in ["/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
    public_paths = ["/api/v1/verify/public", "/api/v1/certificates/verify/", "/api/v3/auth/register-web"]
    is_public = any(request.url.path.startswith(p) for p in public_paths)
    if not is_public:
        return await call_next(request)
    client_ip = request.client.host
    now = datetime.now()
    request_counts[client_ip] = [t for t in request_counts[client_ip] if now - t < timedelta(minutes=1)]
    if len(request_counts[client_ip]) >= 100:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded", "retry_after": 60})
    request_counts[client_ip].append(now)
    return await call_next(request)

# Routers v1
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
app.include_router(certificates_router, prefix="/api/v1")
app.include_router(features_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(network_router, prefix="/api/v1")

# Routers v3
app.include_router(auth_router, prefix="/api/v3")
app.include_router(verification_router, prefix="/api/v3")
app.include_router(admin_router, prefix="/api/v3")
app.include_router(notifications_router, prefix="/api/v3")
app.include_router(network_router, prefix="/api/v3")
app.include_router(invitations_router, prefix="/api/v3")
app.include_router(certificates_router, prefix="/api/v3")
app.include_router(features_router, prefix="/api/v3")

# Endpoint register-web directo
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
    import uuid, os, random, string, logging
    from datetime import datetime
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash
    from app.models import User
    from app.services.email import get_email_service
    logger = logging.getLogger(__name__)
    db = SessionLocal()
    email_service = get_email_service()
    try:
        existing = db.query(User).filter(User.email == request.email).first()
        if existing:
            return {"success": True, "message": "Solicitud recibida"}
        alphabet = string.ascii_letters.replace('O', '').replace('o', '').replace('l', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
        temp_password = ''.join(random.choice(alphabet) for _ in range(12))
        user = User(id=str(uuid.uuid4()), email=request.email, hashed_password=f"temp:{temp_password}", full_name=request.full_name, company_name=request.company_name or "", ruc=request.ruc or "00000000000", plan_type="professional", is_active=True)
        db.add(user)
        db.commit()
        user_email_sent = False
        try:
            user_email_sent = email_service.send_welcome_email(email=request.email, temp_password=temp_password, full_name=request.full_name, plan="professional")
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
        admin_notifications_sent = 0
        try:
            admin_notified = email_service.send_admin_registration_notification(admin_email="tiagomunoz10@icloud.com", user_email=request.email, user_name=request.full_name, user_company=request.company_name or "No especificada", user_ruc=request.ruc or "No especificado", plan="professional")
            if admin_notified: admin_notifications_sent = 1
        except Exception as e:
            logger.error(f"Error notificando admin: {e}")
        return {"success": True, "message": "Usuario registrado exitosamente", "user_id": user.id, "email_sent": user_email_sent, "admin_notifications": admin_notifications_sent, "provider": email_service.provider}
    except Exception as e:
        logger.error(f"[Register Web] Error: {e}")
        return {"success": False, "error": str(e)}
    finally:
        db.close()

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor", "error": str(exc)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Force redeploy Sat Mar 28 03:45:00 AM CST 2026
# Redeploy Sat Mar 28 03:55:04 AM CST 2026
# Redeploy Sat Mar 28 04:05:24 AM CST 2026 - Force build
