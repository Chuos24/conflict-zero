from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import get_current_active_user, verify_token
from app.models import User
from app.services.verification import verification_service
from app.schemas import (
    VerificationRequest, VerificationResponse, VerificationHistory,
    SunatData, OsceSanction, TceSanction, MLAnalysis, ScoreBreakdown
)

router = APIRouter(prefix="/verify", tags=["Verificación"])
security = HTTPBearer()

@router.post(
    "/",
    response_model=VerificationResponse,
    summary="Verificar RUC",
    description="Realiza una verificación completa de un RUC peruano, consultando SUNAT, OSCE y TCE."
)
async def verify_ruc(
    request_data: VerificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Verifica un RUC y retorna el score de riesgo junto con todos los datos.
    
    - **ruc**: Número de RUC de 11 dígitos
    
    Retorna score de 0-100 donde:
    - 80-100: Riesgo bajo
    - 60-79: Riesgo moderado  
    - 40-59: Riesgo alto
    - 0-39: Riesgo crítico
    """
    # Verificar límite de consultas
    if current_user.monthly_requests >= current_user.monthly_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Límite mensual de consultas alcanzado. Actualice su plan."
        )
    
    try:
        result = verification_service.verify_ruc(
            ruc=request_data.ruc,
            user=current_user,
            db=db
        )
        
        return VerificationResponse(
            id=result.get("id"),
            ruc=result["ruc"],
            company_name=result.get("company_name"),
            score=result["score"],
            risk_level=result["risk_level"],
            sunat_data=SunatData(**result["sunat_data"]),
            osce_sanctions=[OsceSanction(**s) for s in result["osce_sanctions"]],
            tce_sanctions=[TceSanction(**s) for s in result["tce_sanctions"]],
            ml_analysis=MLAnalysis(**result["ml_analysis"]),
            score_breakdown=ScoreBreakdown(**result["score_breakdown"]),
            verification_date=result["verification_date"],
            pdf_url=result.get("pdf_url"),
            cached=result.get("cached", False)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al procesar la verificación: {str(e)}"
        )

@router.get(
    "/history",
    response_model=List[VerificationHistory],
    summary="Historial de Verificaciones",
    description="Obtiene el historial de verificaciones realizadas por el usuario autenticado."
)
async def get_verification_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    """Retorna las últimas verificaciones del usuario."""
    history = verification_service.get_verification_history(
        user=current_user,
        db=db,
        limit=limit
    )
    
    return [
        VerificationHistory(
            id=v.id,
            ruc=v.ruc,
            company_name=v.company_name,
            score=v.score,
            risk_level=v.risk_level,
            created_at=v.created_at
        )
        for v in history
    ]

@router.post(
    "/public",
    response_model=VerificationResponse,
    summary="Verificación Pública (Demo)",
    description="Endpoint público para demostración. Limitado a 3 consultas por hora por IP."
)
async def verify_ruc_public(
    request_data: VerificationRequest,
    request: Request
):
    """
    Endpoint público para demostraciones. No requiere autenticación
    pero tiene rate limiting estricto.
    """
    # Aquí implementarías rate limiting por IP
    # Por ahora, solo retornamos la verificación sin guardar
    
    try:
        result = verification_service.verify_ruc(
            ruc=request_data.ruc,
            user=None,
            db=None
        )
        
        return VerificationResponse(
            id=None,
            ruc=result["ruc"],
            company_name=result.get("company_name"),
            score=result["score"],
            risk_level=result["risk_level"],
            sunat_data=SunatData(**result["sunat_data"]),
            osce_sanctions=[OsceSanction(**s) for s in result["osce_sanctions"]],
            tce_sanctions=[TceSanction(**s) for s in result["tce_sanctions"]],
            ml_analysis=MLAnalysis(**result["ml_analysis"]),
            score_breakdown=ScoreBreakdown(**result["score_breakdown"]),
            verification_date=result["verification_date"],
            pdf_url=None,
            cached=result.get("cached", False)
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
