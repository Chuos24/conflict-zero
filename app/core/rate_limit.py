"""
Rate Limiting por Plan — Conflict Zero

Dependency reutilizable para aplicar rate limits según el plan del usuario.
Se integra en routers protegidos vía Depends().
"""

from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User

# ─── Configuración de límites por plan ─────────────────────────────────────

PLAN_RATE_LIMITS = {
    "essential": {"requests_per_minute": 60, "requests_per_day": 1000},
    "professional": {"requests_per_minute": 120, "requests_per_day": 5000},
    "enterprise": {"requests_per_minute": 300, "requests_per_day": 100000},
    # Fallback para usuarios sin plan o plan free (no debería pasar en producción)
    "free": {"requests_per_minute": 10, "requests_per_day": 50},
    "starter": {"requests_per_minute": 30, "requests_per_day": 500},
}

# ─── Storage en memoria (thread-safe) ────────────────────────────────────────

class RateLimitStore:
    """Almacenamiento en memoria para contadores de rate limiting."""
    
    def __init__(self):
        self._data = defaultdict(lambda: {"minute": [], "day": []})
        self._lock = threading.Lock()
    
    def is_allowed(self, key: str, limit_minute: int, limit_day: int) -> tuple[bool, dict]:
        """
        Verifica si una request está dentro de los límites.
        Retorna (allowed, headers_dict).
        """
        now = datetime.utcnow()
        
        with self._lock:
            entry = self._data[key]
            
            # Limpiar entries antiguas
            entry["minute"] = [t for t in entry["minute"] if now - t < timedelta(minutes=1)]
            entry["day"] = [t for t in entry["day"] if now - t < timedelta(days=1)]
            
            # Verificar límites
            minute_remaining = limit_minute - len(entry["minute"])
            day_remaining = limit_day - len(entry["day"])
            
            allowed = minute_remaining > 0 and day_remaining > 0
            
            if allowed:
                entry["minute"].append(now)
                entry["day"].append(now)
                minute_remaining -= 1
                day_remaining -= 1
            
            headers = {
                "X-RateLimit-Limit-Minute": str(limit_minute),
                "X-RateLimit-Remaining-Minute": str(max(0, minute_remaining)),
                "X-RateLimit-Limit-Day": str(limit_day),
                "X-RateLimit-Remaining-Day": str(max(0, day_remaining)),
            }
            
            return allowed, headers
    
    def reset(self, key: str):
        """Resetea los contadores para una key (útil para tests)."""
        with self._lock:
            if key in self._data:
                del self._data[key]


# Singleton global
rate_limit_store = RateLimitStore()


# ─── Dependency para routers ───────────────────────────────────────────────

async def rate_limit_by_plan(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Dependency que aplica rate limiting según el plan del usuario.
    
    Uso:
        @router.post("/verify", dependencies=[Depends(rate_limit_by_plan)])
        async def verify(...)
    
    O inline:
        async def verify(..., _=Depends(rate_limit_by_plan)):
    """
    # Obtener límites según plan
    plan = current_user.plan_type or "free"
    limits = PLAN_RATE_LIMITS.get(plan, PLAN_RATE_LIMITS["free"])
    
    # Key única por usuario
    key = f"user:{current_user.id}"
    
    allowed, headers = rate_limit_store.is_allowed(
        key,
        limit_minute=limits["requests_per_minute"],
        limit_day=limits["requests_per_day"],
    )
    
    # Guardar headers en request.state para que el middleware los inyecte
    request.state.rate_limit_headers = headers
    
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Límite de requests excedido para plan {plan}. "
                   f"Límite: {limits['requests_per_minute']}/min, {limits['requests_per_day']}/día. "
                   f"Upgrade tu plan en https://czperu.com/pricing",
            headers={
                **headers,
                "Retry-After": "60",
            }
        )


# ─── Middleware para inyectar headers ──────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware

class RateLimitHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware que inyecta los headers X-RateLimit-* en la respuesta
    si fueron generados por rate_limit_by_plan.
    """
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        headers = getattr(request.state, "rate_limit_headers", None)
        if headers:
            for header_name, header_value in headers.items():
                response.headers[header_name] = header_value
        
        return response
