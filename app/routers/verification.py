from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import JSONResponse
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

_public_rate_limits: Dict[str, Dict] = {}
PUBLIC_RATE_LIMIT = 3
PUBLIC_RATE_WINDOW = 3600


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_public_rate_limit(ip: str) -> tuple[bool, Dict]:
    now = datetime.utcnow()
    key = hashlib.sha256(ip.encode()).hexdigest()[:16]
    if key not in _public_rate_limits:
        _public_rate_limits[key] = {"count": 1, "reset_at": now + timedelta(seconds=PUBLIC_RATE_WINDOW)}
        return True, {"limit": PUBLIC_RATE_LIMIT, "remaining": PUBLIC_RATE_LIMIT - 1, "reset_at": _public_rate_limits[key]["reset_at"].isoformat()}
    entry = _public_rate_limits[key]
    if now > entry["reset_at"]:
        entry["count"] = 1
        entry["reset_at"] = now + timedelta(seconds=PUBLIC_RATE_WINDOW)
        return True, {"limit": PUBLIC_RATE_LIMIT, "remaining": PUBLIC_RATE_LIMIT - 1, "reset_at": entry["reset_at"].isoformat()}
    if entry["count"] >= PUBLIC_RATE_LIMIT:
        return False, {"limit": PUBLIC_RATE_LIMIT, "remaining": 0, "reset_at": entry["reset_at"].isoformat(), "retry_after": int((entry["reset_at"] - now).total_seconds())}
    entry["count"] += 1
    return True, {"limit": PUBLIC_RATE_LIMIT, "remaining": PUBLIC_RATE_LIMIT - entry["count"], "reset_at": entry["reset_at"].isoformat()}


@router.post("/", response_model=VerificationResponse)
async def verify_ruc(
    request_data: VerificationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if current_user.monthly_requests >= current_user.monthly_limit:
        raise HTTPException(status_code=429, detail="Límite mensual de consultas alcanzado. Actualice su plan.")
    try:
        result = verification_service.verify_ruc(ruc=request_data.ruc, user=current_user, db=db)
        return VerificationResponse(
            id=result.get("id"), ruc=result["ruc"], company_name=result.get("company_name"),
            score=result["score"], risk_level=result["risk_level"],
            sunat_data=SunatData(**result["sunat_data"]),
            osce_sanctions=[OsceSanction(**s) for s in result["osce_sanctions"]],
            tce_sanctions=[TceSanction(**s) for s in result["tce_sanctions"]],
            ml_analysis=MLAnalysis(**result["ml_analysis"]),
            score_breakdown=ScoreBreakdown(**result["score_breakdown"]),
            verification_date=result["verification_date"],
            pdf_url=result.get("pdf_url"), cached=result.get("cached", False)
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


@router.get("/history/search")
async def search_verification_history(
    q: str = "",
    risk_level: str = None,
    score_min: int = None,
    score_max: int = None,
    date_from: str = None,
    date_to: str = None,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    from app.models import VerificationRequest as VR
    from sqlalchemy import or_

    query = db.query(VR).filter(VR.user_id == current_user.id)

    if q and q.strip():
        search_term = f"%{q.strip()}%"
        query = query.filter(or_(VR.ruc.ilike(search_term), VR.company_name.ilike(search_term)))

    if risk_level:
        query = query.filter(VR.risk_level == risk_level)

    if score_min is not None:
        query = query.filter(VR.score >= score_min)
    if score_max is not None:
        query = query.filter(VR.score <= score_max)

    if date_from:
        try:
            dt_from = datetime.fromisoformat(date_from)
            query = query.filter(VR.created_at >= dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.fromisoformat(date_to)
            query = query.filter(VR.created_at <= dt_to)
        except ValueError:
            pass

    total = query.count()
    results = query.order_by(VR.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total, "offset": offset, "limit": limit,
        "results": [{"id": v.id, "ruc": v.ruc, "company_name": v.company_name, "score": v.score, "risk_level": v.risk_level, "created_at": v.created_at.isoformat() if v.created_at else None} for v in results]
    }


@router.post("/public", response_model=VerificationResponse)
async def verify_ruc_public(request_data: VerificationRequest, request: Request):
    client_ip = _get_client_ip(request)
    allowed, rate_info = _check_public_rate_limit(client_ip)
    if not allowed:
        raise HTTPException(status_code=429, detail={"error": "RATE_LIMIT_EXCEEDED", "message": f"Límite de {PUBLIC_RATE_LIMIT} consultas por hora alcanzado.", "reset_at": rate_info["reset_at"]})
    try:
        result = verification_service.verify_ruc(ruc=request_data.ruc, user=None, db=None)
        return VerificationResponse(
            id=None, ruc=result["ruc"], company_name=result.get("company_name"),
            score=result["score"], risk_level=result["risk_level"],
            sunat_data=SunatData(**result["sunat_data"]),
            osce_sanctions=[OsceSanction(**s) for s in result["osce_sanctions"]],
            tce_sanctions=[TceSanction(**s) for s in result["tce_sanctions"]],
            ml_analysis=MLAnalysis(**result["ml_analysis"]),
            score_breakdown=ScoreBreakdown(**result["score_breakdown"]),
            verification_date=result["verification_date"],
            pdf_url=None, cached=result.get("cached", False)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
