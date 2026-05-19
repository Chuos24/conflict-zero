from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, VerificationRequest
from app.schemas import DashboardStats, VerificationHistory

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get(
    "/stats",
    response_model=DashboardStats,
    summary="Estadísticas del Dashboard",
    description="Obtiene estadísticas resumidas para el dashboard del usuario."
)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Retorna estadísticas del usuario:
    - Total de verificaciones realizadas
    - Verificaciones este mes
    - Score promedio de verificaciones
    - Distribución de niveles de riesgo
    - Verificaciones recientes
    """
    from datetime import datetime, timedelta
    
    # Total de verificaciones
    total_verifications = db.query(VerificationRequest).filter(
        VerificationRequest.user_id == current_user.id
    ).count()
    
    # Verificaciones este mes
    first_day_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    verifications_this_month = db.query(VerificationRequest).filter(
        VerificationRequest.user_id == current_user.id,
        VerificationRequest.created_at >= first_day_of_month
    ).count()
    
    # Score promedio
    avg_score_result = db.query(func.avg(VerificationRequest.score)).filter(
        VerificationRequest.user_id == current_user.id
    ).scalar()
    average_score = round(avg_score_result, 2) if avg_score_result else 0.0
    
    # Distribución de riesgo
    risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    risk_counts = db.query(
        VerificationRequest.risk_level,
        func.count(VerificationRequest.id)
    ).filter(
        VerificationRequest.user_id == current_user.id
    ).group_by(VerificationRequest.risk_level).all()
    
    for level, count in risk_counts:
        risk_distribution[level] = count
    
    # Verificaciones recientes
    recent = db.query(VerificationRequest).filter(
        VerificationRequest.user_id == current_user.id
    ).order_by(
        VerificationRequest.created_at.desc()
    ).limit(10).all()
    
    recent_verifications = [
        VerificationHistory(
            id=v.id,
            ruc=v.ruc,
            company_name=v.company_name,
            score=v.score,
            risk_level=v.risk_level,
            created_at=v.created_at
        )
        for v in recent
    ]
    
    return DashboardStats(
        total_verifications=total_verifications,
        verifications_this_month=verifications_this_month,
        average_score=average_score,
        risk_distribution=risk_distribution,
        recent_verifications=recent_verifications
    )

@router.get(
    "/usage",
    summary="Uso del Plan",
    description="Obtiene información sobre el uso del plan actual."
)
async def get_usage_info(
    current_user: User = Depends(get_current_active_user)
):
    """Retorna información de uso del plan actual."""
    return {
        "plan_type": current_user.plan_type,
        "monthly_limit": current_user.monthly_limit,
        "monthly_requests": current_user.monthly_requests,
        "remaining_requests": current_user.monthly_limit - current_user.monthly_requests,
        "reset_date": "Primer día del próximo mes"
    }

@router.get("/stats")
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics for the current user."""
    total_verifications = db.query(Verification).filter(
        Verification.user_id == current_user.id
    ).count()
    
    verifications = db.query(Verification).filter(
        Verification.user_id == current_user.id
    ).all()
    average_score = sum([v.risk_score for v in verifications]) / max(len(verifications), 1) if verifications else 0
    
    from datetime import datetime, timedelta
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    recent_verifications_7d = db.query(Verification).filter(
        Verification.user_id == current_user.id,
        Verification.created_at >= seven_days_ago
    ).count()
    
    return {
        "total_verifications": total_verifications,
        "average_score": round(average_score, 2),
        "recent_verifications_7d": recent_verifications_7d,
        "plan_type": current_user.plan_type,
        "monthly_requests": current_user.monthly_requests,
        "monthly_limit": current_user.monthly_limit
    }
