# Conflict Zero API - Main Application
# Last updated: 2026-03-21 21:00 UTC
# FIX: Founder password corrected to CZ2025!

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.core.config import get_settings
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.models import User
from app.routers import auth_router, verification_router, dashboard_router, health_router, consulta_router
import uuid

settings = get_settings()

# Crear tablas en la base de datos
Base.metadata.create_all(bind=engine)

# Crear usuario founder si no existe - PASSWORD FIX APPLIED
def create_founder_user():
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
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None
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

# Routers
app.include_router(health_router)
app.include_router(consulta_router)  # Endpoint compatible frontend
app.include_router(auth_router, prefix="/api/v1")
app.include_router(verification_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")

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
