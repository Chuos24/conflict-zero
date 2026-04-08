import os
from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(tags=["Debug"])

@router.get("/debug/env", summary="Debug environment variables")
async def debug_env():
    """Muestra todas las variables de entorno disponibles (filtradas)."""
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
