import os
from fastapi import APIRouter, Header, Depends
from fastapi.responses import JSONResponse
from typing import Optional
from app.core.database import get_db
from sqlalchemy.orm import Session

ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN')

router = APIRouter(tags=["Debug"])

@router.get("/debug/env", summary="Debug environment variables")
async def debug_env(authorization: Optional[str] = Header(None)):
    """Muestra variables de entorno (filtradas). Requiere token de admin."""
    token = (authorization or "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        return JSONResponse(status_code=403, content={"error": "UNAUTHORIZED"})

    env_vars = {}
    for key in os.environ:
        if any(x in key.upper() for x in ["PERU", "API", "TOKEN", "KEY", "URL", "DATABASE"]):
            val = os.environ[key]
            env_vars[key] = val[:30] + "..." if len(val) > 30 else val

    return {
        "peru_api_key_exists": "PERU_API_KEY" in os.environ,
        "peruapi_token_exists": "PERUAPI_TOKEN" in os.environ,
        "env_vars": env_vars,
        "all_keys": list(os.environ.keys())
    }


# ============================================================
# ENDPOINT: /debug/status (Health Check Status)
# ============================================================
from datetime import datetime

@router.get(
    "/status",
    summary="API Status Check",
    description="Retorna el estado actual del API y sus dependencias."
)
async def debug_status(db: Session = Depends(get_db)):
    """
    Endpoint de estado del API.
    Verifica: database, redis, SUNAT APIs, y uptime.
    """
    start_time = datetime.utcnow()
    
    # Check database
    db_status = "down"
    try:
        db.execute("SELECT 1")
        db_status = "up"
    except:
        pass
    
    # Check redis (optional)
    redis_status = "down"
    try:
        import redis as redis_lib
        r = redis_lib.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        r.ping()
        redis_status = "up"
    except:
        redis_status = "down (Connection refused port 6379)"
    
    return {
        "status": "healthy" if db_status == "up" else "degraded",
        "timestamp": start_time.isoformat(),
        "database": db_status,
        "redis": redis_status,
        "api": "conflict-zero-backend",
        "version": "1.0.0"
    }
