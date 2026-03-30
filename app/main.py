# Conflict Zero API - Main Application
# Last updated: 2026-03-28 03:55 UTC - LegalBot V3.0 Deploy
# FIX: CAP scoring - sanciones vigentes check
# FIX: Founder password corrected to CZ2025!
# NEW: LegalBot V3.0 - Scoring Multidimensional
# NEW: Added compare router for multi-RUC comparison

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
from app.routers import auth_router, verification_router, dashboard_router, health_router, consulta_router, debug_router, compare_router, payments_router
import uuid

settings = get_settings()

print("🚀 Starting Conflict Zero API - LegalBot V3.0")

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

# Crear usuario founder si no existe - PASSWORD FIX APPLIED
def create_founder_user():
    if not db_connected:
        print("⚠️ Saltando creación de founder (sin conexión a DB)")
        return
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == "founder@conflictzero.com").first()
        if not existing:
            # Hash pre-calculado de "CZ2025!" - evita problemas con bcrypt en Render
            PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
            founder = User(
                id=str(uuid.uuid4()),
                email="founder@conflictzero.com",
                hashed_password=PRECOMPUTED_HASH,  # FIXED: Precomputed hash
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
    if request.url.path in ["/api/v1/health", "/docs", "/redoc", "/openapi.json"]:
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

# Routers v3 (para compatibilidad con frontend)
app.include_router(auth_router, prefix="/api/v3")
app.include_router(verification_router, prefix="/api/v3")

# Manejo de excepciones
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor", "error": str(exc)}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
# Force redeploy Sat Mar 28 03:45:00 AM CST 2026 - LegalBot Universal V2.0
# LegalBot V3.0 Redeploy Sat Mar 28 03:55:04 AM CST 2026
# Redeploy Sat Mar 28 03:57:58 AM CST 2026
# Redeploy Sat Mar 28 04:05:24 AM CST 2026 - Force build
# Force deploy Sat Mar 28 04:14:44 AM CST 2026
