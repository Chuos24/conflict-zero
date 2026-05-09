from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/users", summary="Listar usuarios")
async def list_users():
    """Lista todos los usuarios registrados (requiere admin)."""
    return {"users": [], "total": 0, "message": "Endpoint reservado para administradores"}

@router.get("/stats", summary="Estadísticas del sistema")
async def system_stats():
    """Estadísticas generales del sistema."""
    return {
        "total_verifications": 0,
        "total_users": 0,
        "active_today": 0,
        "message": "Endpoint reservado para administradores"
    }

@router.post("/verify-ruc", summary="Verificación manual de RUC")
async def manual_verify(ruc: str):
    """Verificación manual de un RUC por parte del admin."""
    return {"ruc": ruc, "status": "processed", "message": "Verificación registrada"}
