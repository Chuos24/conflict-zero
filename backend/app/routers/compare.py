"""
Router para comparación de múltiples RUCs
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.core.rate_limit import rate_limit_dependency
from app.models import User
from app.services.compare_service import compare_rucs

router = APIRouter(prefix="/compare", tags=["Comparación"])


class CompareRequest(BaseModel):
    rucs: List[str] = Field(..., min_length=2, max_length=10, description="Lista de RUCs a comparar (2-10)")


class CompareResult(BaseModel):
    ruc: str
    razon_social: str
    score: int
    risk_level: str
    estado_sunat: str
    condicion: str
    sanciones_osce: int
    sanciones_tce: int
    deuda_sunat: float
    fines_detalle: list


class ComparisonSummary(BaseModel):
    average_score: float
    best_ruc: dict | None
    worst_ruc: dict | None
    risk_distribution: dict
    score_range: dict


class CompareResponse(BaseModel):
    total_compared: int
    successful: int
    failed: int
    results: List[CompareResult]
    errors: List[dict]
    comparison_summary: ComparisonSummary


@router.post(
    "",
    response_model=CompareResponse,
    summary="Comparar múltiples RUCs",
    description="Compara hasta 10 RUCs simultáneamente y retorna resultados ordenados por score de riesgo."
)
async def compare_rucs_endpoint(
    request: CompareRequest,
    current_user: User = Depends(get_current_active_user),
    rate_limit: dict = Depends(rate_limit_dependency),
    db: Session = Depends(get_db)
):
    """
    Endpoint para comparar múltiples RUCs.
    
    - **Essential**: máximo 2 RUCs
    - **Professional**: máximo 5 RUCs  
    - **Enterprise**: máximo 10 RUCs
    """
    # Validar límites según plan
    plan_limits = {
        "essential": 2,
        "professional": 5,
        "enterprise": 10
    }
    
    user_limit = plan_limits.get(current_user.plan_type, 2)
    
    if len(request.rucs) > user_limit:
        raise HTTPException(
            status_code=403,
            detail=f"Su plan {current_user.plan_type} permite comparar máximo {user_limit} RUCs. "
                   f"Actualice su plan para comparar más RUCs."
        )
    
    # Validar formato de RUCs
    invalid_rucs = [ruc for ruc in request.rucs if len(ruc) != 11 or not ruc.isdigit()]
    if invalid_rucs:
        raise HTTPException(
            status_code=400,
            detail=f"RUCs inválidos: {', '.join(invalid_rucs)}. Deben tener 11 dígitos numéricos."
        )
    
    # Eliminar duplicados manteniendo orden
    unique_rucs = list(dict.fromkeys(request.rucs))
    
    # Realizar comparación
    result = await compare_rucs(unique_rucs, db)
    
    return result


@router.get(
    "/limits",
    summary="Obtener límites de comparación",
    description="Retorna los límites de comparación según el plan del usuario."
)
async def get_compare_limits(
    current_user: User = Depends(get_current_active_user),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    """Retorna los límites de comparación para el usuario actual."""
    plan_limits = {
        "essential": 2,
        "professional": 5,
        "enterprise": 10
    }
    
    return {
        "plan_type": current_user.plan_type,
        "max_rucs": plan_limits.get(current_user.plan_type, 2),
        "limits_by_plan": plan_limits
    }
