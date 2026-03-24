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
