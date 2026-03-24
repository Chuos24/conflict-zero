from fastapi import APIRouter
from datetime import datetime
from sqlalchemy import text
from app.core.cache import cache
from app.core.database import engine
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["Salud"])

@router.get(
    "/health",
    summary="Health Check",
    description="Verifica el estado de los servicios de la aplicación."
)
async def health_check():
    """Endpoint de health check para monitoreo."""
    health_status = {
        "status": "healthy",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Check Database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        health_status["services"]["database"] = "up"
    except Exception as e:
        health_status["services"]["database"] = f"down: {str(e)}"
        health_status["status"] = "degraded"
    
    # Check Redis
    try:
        cache.client.ping()
        health_status["services"]["redis"] = "up"
    except Exception as e:
        health_status["services"]["redis"] = f"down: {str(e)}"
        health_status["status"] = "degraded"
    
    return health_status

@router.get(
    "/debug/env",
    summary="Debug Environment Variables",
    description="Muestra variables de entorno relacionadas con APIs (solo nombres, no valores completos)."
)
async def debug_env():
    """Endpoint de debug para verificar variables de entorno."""
    import os
    peru_api_key = os.getenv("PERU_API_KEY", "NOT_SET")
    peruapi_token = os.getenv("PERUAPI_TOKEN", "NOT_SET")
    
    return {
        "PERU_API_KEY_set": peru_api_key != "NOT_SET",
        "PERU_API_KEY_length": len(peru_api_key) if peru_api_key != "NOT_SET" else 0,
        "PERU_API_KEY_prefix": peru_api_key[:20] if peru_api_key != "NOT_SET" else "N/A",
        "PERUAPI_TOKEN_set": peruapi_token != "NOT_SET",
        "PERUAPI_TOKEN_length": len(peruapi_token) if peruapi_token != "NOT_SET" else 0,
        "settings_PERU_API_KEY": settings.PERU_API_KEY[:20] if settings.PERU_API_KEY else "N/A",
        "settings_PERUAPI_TOKEN": settings.PERUAPI_TOKEN[:20] if settings.PERUAPI_TOKEN else "N/A",
    }

@router.get(
    "/",
    summary="API Info",
    description="Información básica de la API."
)
async def root():
    """Endpoint raíz con información de la API."""
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "documentation": "/docs",
        "health": "/health"
    }
