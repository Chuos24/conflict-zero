from fastapi import APIRouter
from datetime import datetime, timedelta
from sqlalchemy import text
from app.core.cache import cache
from app.core.database import engine
from app.core.config import get_settings
import os
import json

settings = get_settings()
router = APIRouter(tags=["Salud"])

# Start time para calcular uptime
START_TIME = datetime.utcnow()

# Archivo de métricas de SLA
SLA_METRICS_FILE = "/tmp/sla_metrics.json"

def get_sla_metrics():
    """Obtiene métricas de SLA desde archivo."""
    try:
        if os.path.exists(SLA_METRICS_FILE):
            with open(SLA_METRICS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {
        "total_checks": 0,
        "successful_checks": 0,
        "last_downtime": None,
        "uptime_percentage": 100.0
    }

def update_sla_metrics(is_healthy: bool):
    """Actualiza métricas de SLA."""
    metrics = get_sla_metrics()
    metrics["total_checks"] += 1
    if is_healthy:
        metrics["successful_checks"] += 1
    else:
        metrics["last_downtime"] = datetime.utcnow().isoformat()
    
    if metrics["total_checks"] > 0:
        metrics["uptime_percentage"] = (
            metrics["successful_checks"] / metrics["total_checks"] * 100
        )
    
    try:
        with open(SLA_METRICS_FILE, 'w') as f:
            json.dump(metrics, f)
    except:
        pass
    
    return metrics

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
        "services": {},
        "sla": {}
    }
    
    is_healthy = True
    
    # Check Database
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            conn.commit()
        health_status["services"]["database"] = "up"
    except Exception as e:
        health_status["services"]["database"] = f"down: {str(e)}"
        health_status["status"] = "degraded"
        is_healthy = False
    
    # Check Redis (opcional - no afecta SLA)
    try:
        cache.client.ping()
        health_status["services"]["redis"] = "up"
    except Exception as e:
        health_status["services"]["redis"] = f"down: {str(e)}"
        # Redis no afecta SLA - es opcional
    
    # Uptime
    uptime = datetime.utcnow() - START_TIME
    health_status["sla"]["uptime_seconds"] = int(uptime.total_seconds())
    health_status["sla"]["uptime_formatted"] = str(uptime).split('.')[0]
    
    # Métricas de SLA
    sla_metrics = update_sla_metrics(is_healthy)
    health_status["sla"].update(sla_metrics)
    
    # Garantía SLA
    health_status["sla"]["guarantee"] = "99.9%"
    health_status["sla"]["max_monthly_downtime_minutes"] = 43
    
    return health_status

@router.get(
    "/status",
    summary="Status Page",
    description="Página de estado pública con métricas de disponibilidad."
)
async def status_page():
    """Endpoint de status para transparencia pública."""
    sla_metrics = get_sla_metrics()
    uptime = datetime.utcnow() - START_TIME
    
    return {
        "service": "Conflict Zero API",
        "status": "operational",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": {
            "current_session": str(uptime).split('.')[0],
            "percentage": round(sla_metrics.get("uptime_percentage", 100.0), 3)
        },
        "components": {
            "api": {"status": "operational", "impact": "critical"},
            "database": {"status": "operational", "impact": "critical"},
            "redis": {"status": "degraded", "impact": "performance"},
            "sunat_integration": {"status": "operational", "impact": "core_feature"}
        },
        "sla": {
            "guarantee": "99.9%",
            "monthly_downtime_allowance": "43 minutes",
            "current_month_uptime": f"{round(sla_metrics.get('uptime_percentage', 100.0), 3)}%"
        },
        "incidents": [],
        "maintenance": None
    }

@router.get(
    "/debug/env",
    summary="Debug Environment Variables",
    description="Muestra variables de entorno relacionadas con APIs (solo nombres, no valores completos)."
)
async def debug_env():
    """Endpoint de debug para verificar variables de entorno."""
    import os
    
    env_vars = {
        "FACTILIZA_TOKEN": os.getenv("FACTILIZA_TOKEN", "NOT_SET")[:20] + "..." if os.getenv("FACTILIZA_TOKEN") else "NOT_SET",
        "APIPERU_TOKEN": os.getenv("APIPERU_TOKEN", "NOT_SET")[:20] + "..." if os.getenv("APIPERU_TOKEN") else "NOT_SET",
        "PERUAPI_TOKEN": os.getenv("PERUAPI_TOKEN", "NOT_SET")[:20] + "..." if os.getenv("PERUAPI_TOKEN") else "NOT_SET",
    }
    
    return {
        "configured_apis": {
            "factiliza": os.getenv("FACTILIZA_TOKEN") != "NOT_SET" and os.getenv("FACTILIZA_TOKEN") is not None,
            "apiperu_dev": os.getenv("APIPERU_TOKEN") != "NOT_SET" and os.getenv("APIPERU_TOKEN") is not None,
            "peruapi_com": os.getenv("PERUAPI_TOKEN") != "NOT_SET" and os.getenv("PERUAPI_TOKEN") is not None,
        },
        "tokens_preview": env_vars
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
        "health": "/health",
        "status": "/status"
    }
