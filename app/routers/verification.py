from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime, timedelta
import hashlib

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

# ─── Rate Limiting por IP para /verify/public ──────────────────────────────
# Almacenamiento en memoria (para producción usar Redis)
_public_rate_limits: Dict[str, Dict] = {}

PUBLIC_RATE_LIMIT = 3  # consultas por hora
PUBLIC_RATE_WINDOW = 3600  # segundos (1 hora)


def _get_client_ip(request: Request) -> str:
    """Obtiene la IP real del cliente considerando proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_public_rate_limit(ip: str) -> tuple[bool, Dict]:
    """
    Verifica si la IP está dentro del rate limit.
    Retorna (allowed, rate_limit_info).
    """
    now = datetime.utcnow()
    key = hashlib.sha256(ip.encode()).hexdigest()[:16]
    
    if key not in _public_rate_limits:
        _public_rate_limits[key] = {
            "count": 1,
            "reset_at": now + timedelta(seconds=PUBLIC_RATE_WINDOW),
            "first_request": now
        }
        return True, {
            "limit": PUBLIC_RATE_LIMIT,
            "remaining": PUBLIC_RATE_LIMIT - 1,
            "reset_at": _public_rate_limits[key]["reset_at"].isoformat()
        }
    
    entry = _public_rate_limits[key]
    
    # Resetear si pasó la ventana
    if now > entry["reset_at"]:
        entry["count"] = 1
        entry["reset_at"] = now + timedelta(seconds=PUBLIC_RATE_WINDOW)
        entry["first_request"] = now
        return True, {
            "limit": PUBLIC_RATE_LIMIT,
            "remaining": PUBLIC_RATE_LIMIT - 1,
            "reset_at": entry["reset_at"].isoformat()
        }
    
    # Verificar límite
    if entry["count"] >= PUBLIC_RATE_LIMIT:
        return False, {
            "limit": PUBLIC_RATE_LIMIT,
            "remaining": 0,
            "reset_at": entry["reset_at"].isoformat(),
            "retry_after": int((entry["reset_at"] - now).total_seconds())
        }
    
    entry["count"] += 1
    return True, {
        "limit": PUBLIC_RATE_LIMIT,
        "remaining": PUBLIC_RATE_LIMIT - entry["count"],
        "reset_at": entry["reset_at"].isoformat()
    }

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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.get("/history", response_model=List[VerificationHistory])
async def get_verification_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 50
):
    history = verification_service.get_verification_history(user=current_user, db=db, limit=limit)
    return [VerificationHistory(id=v.id, ruc=v.ruc, company_name=v.company_name, score=v.score, risk_level=v.risk_level, created_at=v.created_at) for v in history]

@router.post("/public", response_model=VerificationResponse)
async def verify_ruc_public(request_data: VerificationRequest, request: Request):
    client_ip = _get_client_ip(request)
    allowed, rate_info = _check_public_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail={"error": "RATE_LIMIT_EXCEEDED", "message": f"Límite de {PUBLIC_RATE_LIMIT} consultas por hora alcanzado.", "reset_at": rate_info["reset_at"]})
    try:
        result = verification_service.verify_ruc(ruc=request_data.ruc, user=None, db=None)
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
        raise HTTPException(status_code=400, detail=str(e))
