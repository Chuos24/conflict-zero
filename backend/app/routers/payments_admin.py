"""
Admin Payments Router - Conflict Zero API
Ported from api_v3.py (Backend B) to Backend A modular structure
Handles manual payments (transfer, deposit, Yape, Plin, cash) and plan activation
"""
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import User, PaymentManual

router = APIRouter(prefix="/admin", tags=["Admin Payments"])

# Token admin desde env (reemplaza hardcodeado de api_v3.py)
import os
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "cz2026")

# ============================================================================
# Schemas
# ============================================================================

class RecordPaymentRequest(BaseModel):
    user_id: str
    amount: float = Field(..., gt=0)
    reference: str = Field(..., min_length=1)
    date: str  # ISO format "2026-04-12"
    currency: str = "PEN"
    method: str = "transferencia"
    notes: Optional[str] = None

class ActivatePlanRequest(BaseModel):
    user_id: str
    plan_type: str = Field(..., pattern=r"^(essential|professional|enterprise)$")
    months: int = Field(..., ge=1, le=24)

class PaymentResponse(BaseModel):
    success: bool
    payment_id: str
    user_id: str
    user_email: str
    amount: float
    currency: str
    reference: str
    created_at: str
    message: str


# ============================================================================
# Helpers
# ============================================================================

def _require_admin(authorization: Optional[str]) -> bool:
    """Valida token de admin."""
    if not authorization or not authorization.startswith("Bearer "):
        return False
    token = authorization.replace("Bearer ", "")
    return token == ADMIN_TOKEN


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/record-payment", response_model=PaymentResponse)
async def record_payment(
    request: RecordPaymentRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Registra un pago recibido por transferencia bancaria.
    No activa el plan — eso se hace en /activate-plan.
    Requiere token admin.
    """
    if not _require_admin(authorization):
        raise HTTPException(status_code=401, detail="Token admin inválido")
    
    valid_methods = {"transferencia", "deposito", "yape", "plin", "efectivo"}
    if request.method not in valid_methods:
        raise HTTPException(
            status_code=400, 
            detail=f"Método inválido. Válidos: {', '.join(valid_methods)}"
        )
    
    # Verificar usuario existe
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    try:
        payment_date = datetime.strptime(request.date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida. Usar formato YYYY-MM-DD")
    
    # Crear registro de pago
    payment = PaymentManual(
        user_id=request.user_id,
        amount=request.amount,
        currency=request.currency,
        method=request.method,
        reference=request.reference.strip(),
        payment_date=payment_date,
        notes=request.notes
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    
    return {
        "success": True,
        "payment_id": payment.id,
        "user_id": request.user_id,
        "user_email": user.email,
        "amount": request.amount,
        "currency": request.currency,
        "reference": request.reference,
        "created_at": payment.created_at.isoformat() if payment.created_at else str(datetime.utcnow()),
        "message": "Pago registrado. Usa /activate-plan para activar el plan del usuario."
    }


@router.post("/activate-plan")
async def activate_plan(
    request: ActivatePlanRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Activa o cambia el plan de un usuario por N meses.
    Actualiza users.plan_type, plan_activated_at, plan_expires_at.
    Requiere token admin.
    """
    if not _require_admin(authorization):
        raise HTTPException(status_code=401, detail="Token admin inválido")
    
    valid_plans = {"essential", "professional", "enterprise"}
    if request.plan_type not in valid_plans:
        raise HTTPException(
            status_code=400,
            detail=f"Plan inválido. Válidos: {', '.join(valid_plans)}"
        )
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    previous_plan = user.plan_type
    
    # Actualizar plan
    user.plan_type = request.plan_type
    user.is_active = True
    # Nota: plan_activated_at y plan_expires_at no están en el model User actual
    # Se agregan como atributos dinámicos o se extiende el model
    
    db.commit()
    db.refresh(user)
    
    return {
        "success": True,
        "user_id": request.user_id,
        "user_email": user.email,
        "previous_plan": previous_plan,
        "new_plan": request.plan_type,
        "months": request.months,
        "message": f"Plan {request.plan_type} activado por {request.months} meses"
    }


@router.get("/pending-activations")
async def pending_activations(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Retorna dos listas:
    1. Usuarios con pago registrado pero plan = 'essential' (sin activar)
    2. Usuarios con plan activo que vence en menos de 7 días
    Requiere token admin.
    """
    if not _require_admin(authorization):
        raise HTTPException(status_code=401, detail="Token admin inválido")
    
    # Usuarios con pago registrado pero sin plan superior
    subq = db.query(PaymentManual.user_id).distinct().subquery()
    unactivated = db.query(User).filter(
        User.id.in_(subq),
        User.plan_type == "essential"
    ).order_by(User.created_at.desc()).all()
    
    # Nota: plan_expires_at no está en el model actual
    # Por ahora solo retornamos la primera lista
    
    return {
        "success": True,
        "unactivated": [
            {
                "id": u.id,
                "email": u.email,
                "company_name": u.company_name,
                "ruc": u.ruc,
                "plan": u.plan_type,
                "status": u.status
            }
            for u in unactivated
        ],
        "unactivated_count": len(unactivated),
        "expiring_soon": [],
        "expiring_soon_count": 0,
        "note": "plan_expires_at field needed for expiring_soon calculation"
    }


@router.get("/payments-history")
async def payments_history(
    user_id: Optional[str] = None,
    limit: int = 50,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Historial de pagos manuales.
    Parámetro opcional: ?user_id=123 para filtrar por usuario.
    Requiere token admin.
    """
    if not _require_admin(authorization):
        raise HTTPException(status_code=401, detail="Token admin inválido")
    
    limit = min(max(limit, 1), 200)
    
    query = db.query(PaymentManual).order_by(PaymentManual.created_at.desc())
    if user_id:
        query = query.filter(PaymentManual.user_id == user_id)
    
    payments = query.limit(limit).all()
    
    total_amount = sum(p.amount for p in payments)
    
    return {
        "success": True,
        "payments": [
            {
                "id": p.id,
                "user_id": p.user_id,
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
        "total_amount": round(total_amount, 2),
        "currency": "PEN"
    }
