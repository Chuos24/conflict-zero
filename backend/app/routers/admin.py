from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from app.core.rate_limit import rate_limit_dependency
from app.core.security import get_current_active_user
from app.models.user import User
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", summary="Listar usuarios")
async def list_users(
    current_user: User = Depends(get_current_active_user),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Lista todos los usuarios registrados (requiere admin)."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Se requieren privilegios de administrador")
    return {"users": [], "total": 0, "message": "Endpoint activo - implementar query"}

@router.get("/stats", summary="Estadísticas del sistema")
async def system_stats(
    current_user: User = Depends(get_current_active_user),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Estadísticas generales del sistema."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Se requieren privilegios de administrador")
    return {
        "total_verifications": 0,
        "total_users": 0,
        "active_today": 0,
        "message": "Endpoint activo - implementar query"
    }

@router.post("/verify-ruc", summary="Verificación manual de RUC")
async def manual_verify(
    ruc: str,
    current_user: User = Depends(get_current_active_user),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Verificación manual de un RUC por parte del admin."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Se requieren privilegios de administrador")
    return {"ruc": ruc, "status": "processed", "message": "Verificación registrada"}
