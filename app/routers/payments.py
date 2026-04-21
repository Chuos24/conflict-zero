"""
Payments Router - Conflict Zero API
Provides payment status and links to admin payment management.
Admin endpoints moved to payments_admin.py under /api/v3/admin/*
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_active_user, verify_token
from app.models import User, PaymentManual

router = APIRouter(prefix="/payments", tags=["Pagos"])


@router.get("/")
async def payments_root():
    """Root endpoint with links to payment management."""
    return {
        "message": "Payments API",
        "admin_endpoints": {
            "record_payment": "POST /api/v3/admin/record-payment",
            "activate_plan": "POST /api/v3/admin/activate-plan",
            "pending_activations": "GET /api/v3/admin/pending-activations",
            "payments_history": "GET /api/v3/admin/payments-history"
        },
        "note": "Admin endpoints require Bearer token authorization"
    }


@router.get("/history")
async def get_my_payments(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get payment history for the authenticated user.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token requerido")
    
    token = authorization.replace("Bearer ", "")
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    payments = db.query(PaymentManual).filter(
        PaymentManual.user_id == user_id
    ).order_by(PaymentManual.created_at.desc()).all()
    
    return {
        "success": True,
        "user_id": user_id,
        "user_email": user.email,
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "currency": p.currency,
                "method": p.method,
                "reference": p.reference,
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "notes": p.notes,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in payments
        ],
        "count": len(payments),
        "plan_type": user.plan_type
    }
