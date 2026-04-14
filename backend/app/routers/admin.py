from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])

ADMIN_PASSWORD = "cz2026"

class ApproveUserRequest(BaseModel):
    approved: bool = True
    notes: Optional[str] = None

@router.get("/pending-users")
async def get_pending_users(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Obtener usuarios pendientes de aprobación"""
    # Verificar token admin
    if not authorization or authorization.replace("Bearer ", "") != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Token inválido")
    
    try:
        users = db.query(User).filter(User.status == "pending_approval").all()
        
        return {
            "success": True,
            "pending_count": len(users),
            "users": [
                {
                    "id": u.id,
                    "ruc": u.ruc,
                    "business_name": u.business_name or u.company_name,
                    "email": u.email,
                    "plan": u.plan_type,
                    "score_at_registration": getattr(u, 'score_at_registration', None),
                    "status": u.status,
                    "created_at": u.created_at.isoformat() if u.created_at else None
                }
                for u in users
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/approve-user/{user_id}")
async def approve_user(
    user_id: str,
    request: ApproveUserRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """Aprobar o rechazar usuario"""
    # Verificar token admin
    if not authorization or authorization.replace("Bearer ", "") != ADMIN_PASSWORD:
        raise HTTPException(status_code=403, detail="Token inválido")
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user.status = "active" if request.approved else "rejected"
        db.commit()
        
        return {
            "success": True,
            "message": f"Usuario {'aprobado' if request.approved else 'rechazado'}",
            "user_id": user_id,
            "status": user.status
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
