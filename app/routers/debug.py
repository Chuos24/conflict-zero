import os
from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from typing import Optional

ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN')
if not ADMIN_TOKEN:
    raise RuntimeError("ADMIN_TOKEN environment variable is required")

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
