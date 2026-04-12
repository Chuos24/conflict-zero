"""
Admin Router - Payment System + Plan Activation
Endpoints para gestión de pagos manuales y activación de planes
"""

from fastapi import APIRouter, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import jwt

# Database
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])

# Config
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')
JWT_SECRET = os.environ.get('JWT_SECRET', 'conflict-zero-secret-key-2024')


# ============ PYDANTIC MODELS ============

class RecordPaymentRequest(BaseModel):
    user_id: str  # UUID string, e.g. "550e8400-e29b-41d4-a716-446655440000"
    amount: float
    currency: str = "PEN"
    method: str = "transferencia"  # transferencia, deposito, yape, plin, efectivo
    reference: str
    date: str  # YYYY-MM-DD
    notes: Optional[str] = None


class ActivatePlanRequest(BaseModel):
    user_id: str  # UUID string
    plan_type: str  # starter | professional | enterprise
    months: int  # 1-24


class PaymentResponse(BaseModel):
    success: bool
    payment_id: Optional[int] = None
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    reference: Optional[str] = None
    created_at: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


class PlanActivationResponse(BaseModel):
    success: bool
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    previous_plan: Optional[str] = None
    new_plan: Optional[str] = None
    months: Optional[int] = None
    activated_at: Optional[str] = None
    expires_at: Optional[str] = None
    error: Optional[str] = None


class PendingActivationsResponse(BaseModel):
    success: bool
    unactivated: List[Dict[str, Any]] = []
    unactivated_count: int = 0
    expiring_soon: List[Dict[str, Any]] = []
    expiring_soon_count: int = 0
    error: Optional[str] = None


class PaymentHistoryResponse(BaseModel):
    success: bool
    payments: List[Dict[str, Any]] = []
    count: int = 0
    total_amount: float = 0
    currency: str = "PEN"
    error: Optional[str] = None


# ============ AUTH HELPER ============

def _require_admin(authorization: Optional[str]) -> bool:
    """Valida token de admin. Retorna True si es válido."""
    if not authorization or not authorization.startswith('Bearer '):
        return False
    token = authorization.replace('Bearer ', '')
    if token == ADMIN_TOKEN:
        return True
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return payload.get('type') == 'admin' or bool(payload.get('is_admin'))
    except Exception:
        pass
    return False


# ============ ENDPOINTS ============

@router.get("/")
async def admin_root():
    """Root endpoint - info básica"""
    return {"message": "Admin API - Payment System v1.0", "endpoints": [
        "/record-payment",
        "/activate-plan", 
        "/pending-activations",
        "/payments-history"
    ]}


@router.post("/record-payment", response_model=PaymentResponse)
async def record_payment(request: RecordPaymentRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Registra un pago recibido por transferencia bancaria.
    No activa el plan — eso se hace en /activate-plan.
    Requiere token admin.
    """
    if not _require_admin(authorization):
        return JSONResponse(status_code=401, content={'success': False, 'error': 'UNAUTHORIZED'})

    # Validar método
    valid_methods = {'transferencia', 'deposito', 'yape', 'plin', 'efectivo'}
    if request.method not in valid_methods:
        return JSONResponse(status_code=400, content={
            'success': False, 'error': 'INVALID_METHOD',
            'valid': list(valid_methods)
        })
    
    if request.amount <= 0:
        return JSONResponse(status_code=400, content={'success': False, 'error': 'INVALID_AMOUNT'})

    # Verificar que el usuario existe
    user = db.query(User).filter(User.id == str(request.user_id)).first()
    if not user:
        return JSONResponse(status_code=404, content={'success': False, 'error': 'USER_NOT_FOUND'})

    try:
        # Importar modelo de payments_manual
        from app.models import PaymentManual
        
        payment = PaymentManual(
            user_id=request.user_id,
            amount=request.amount,
            currency=request.currency,
            method=request.method,
            reference=request.reference.strip(),
            payment_date=request.date,
            notes=request.notes,
            created_by='admin'
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        print(f"[Payments] ✅ Pago registrado: user={request.user_id}, ref={request.reference}, S/{request.amount}")
        return {
            'success': True,
            'payment_id': payment.id,
            'user_id': request.user_id,
            'user_email': user.email,
            'amount': request.amount,
            'currency': request.currency,
            'reference': request.reference,
            'created_at': str(payment.created_at),
            'message': f'Pago registrado. Usa /activate-plan para activar el plan del usuario.',
        }
    except Exception as e:
        db.rollback()
        print(f"[Payments] Error: {e}")
        return JSONResponse(status_code=500, content={'success': False, 'error': 'DB_ERROR', 'message': str(e)})


@router.post("/activate-plan", response_model=PlanActivationResponse)
async def activate_plan(request: ActivatePlanRequest, authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Activa o cambia el plan de un usuario por N meses.
    Actualiza users.plan, plan_activated_at, plan_expires_at.
    Requiere token admin.
    """
    if not _require_admin(authorization):
        return JSONResponse(status_code=401, content={'success': False, 'error': 'UNAUTHORIZED'})

    valid_plans = {'starter', 'professional', 'enterprise'}
    if request.plan_type not in valid_plans:
        return JSONResponse(status_code=400, content={
            'success': False, 'error': 'INVALID_PLAN',
            'valid': list(valid_plans)
        })
    if request.months < 1 or request.months > 24:
        return JSONResponse(status_code=400, content={'success': False, 'error': 'INVALID_MONTHS', 'valid': '1-24'})

    user = db.query(User).filter(User.id == str(request.user_id)).first()
    if not user:
        return JSONResponse(status_code=404, content={'success': False, 'error': 'USER_NOT_FOUND'})

    # Límites mensuales por plan
    PLAN_LIMITS = {
        'starter': 1000,
        'professional': 5000,
        'enterprise': 100000,
    }

    try:
        previous_plan = user.plan

        # Actualizar AMBAS columnas de plan para que todo el sistema vea el cambio
        user.plan = request.plan_type
        user.plan_type = request.plan_type
        user.monthly_limit = PLAN_LIMITS.get(request.plan_type, 1000)
        user.plan_activated_at = datetime.utcnow()
        user.plan_expires_at = datetime.utcnow() + timedelta(days=30 * request.months)
        user.is_active = True
        
        db.commit()
        db.refresh(user)

        expires_at = str(user.plan_expires_at)
        print(f"[Plans] ✅ Plan activado: user={request.user_id}, plan={request.plan_type}, meses={request.months}, vence={expires_at}")

        return {
            'success': True,
            'user_id': request.user_id,
            'user_email': user.email,
            'previous_plan': previous_plan,
            'new_plan': request.plan_type,
            'months': request.months,
            'activated_at': str(user.plan_activated_at),
            'expires_at': expires_at,
        }
    except Exception as e:
        db.rollback()
        print(f"[Plans] Error: {e}")
        return JSONResponse(status_code=500, content={'success': False, 'error': 'DB_ERROR', 'message': str(e)})


@router.get("/pending-activations", response_model=PendingActivationsResponse)
async def pending_activations(authorization: str = Header(None), db: Session = Depends(get_db)):
    """
    Retorna dos listas:
    1. Usuarios con pago registrado pero plan = 'free' (sin activar)
    2. Usuarios con plan activo que vence en menos de 7 días
    """
    if not _require_admin(authorization):
        return JSONResponse(status_code=401, content={'success': False, 'error': 'UNAUTHORIZED'})

    try:
        from sqlalchemy import text
        
        # Usuarios con pago registrado pero sin plan activado (plan = 'free')
        # Query compatible con SQLite (no usa DISTINCT ON)
        query_unactivated = """
            SELECT u.id, u.email, u.company_name, u.plan,
                   pm.amount, pm.currency, pm.method, pm.reference, pm.payment_date, pm.created_at as payment_registered_at
            FROM users u
            JOIN (
                SELECT user_id, MAX(created_at) as max_created_at
                FROM payments_manual
                GROUP BY user_id
            ) latest ON latest.user_id = u.id
            JOIN payments_manual pm ON pm.user_id = u.id AND pm.created_at = latest.max_created_at
            WHERE u.plan = 'free'
            ORDER BY pm.created_at DESC
        """
        result = db.execute(text(query_unactivated))
        unactivated = [dict(row._mapping) for row in result]
        for r in unactivated:
            for k in ('payment_date', 'payment_registered_at'):
                if r.get(k):
                    r[k] = str(r[k])

        # Usuarios con plan expirando en menos de 7 días
        # Query compatible con SQLite (usa datetime en lugar de NOW() + INTERVAL)
        from datetime import datetime, timedelta
        seven_days_from_now = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        query_expiring = """
            SELECT
                u.id, u.email, u.company_name, u.plan,
                u.plan_activated_at, u.plan_expires_at
            FROM users u
            WHERE u.plan != 'free'
                AND u.plan_expires_at IS NOT NULL
                AND u.plan_expires_at <= :seven_days
            ORDER BY u.plan_expires_at ASC
        """
        result = db.execute(text(query_expiring), {"seven_days": seven_days_from_now})
        expiring_soon = [dict(row._mapping) for row in result]
        for r in expiring_soon:
            for k in ('plan_activated_at', 'plan_expires_at'):
                if r.get(k):
                    r[k] = str(r[k])
            # Calcular days_left manualmente
            if r.get('plan_expires_at'):
                expires = datetime.fromisoformat(r['plan_expires_at'].replace('Z', '+00:00').replace('+00:00', ''))
                r['days_left'] = (expires - datetime.utcnow()).days
            else:
                r['days_left'] = None

        return {
            'success': True,
            'unactivated': unactivated,
            'unactivated_count': len(unactivated),
            'expiring_soon': expiring_soon,
            'expiring_soon_count': len(expiring_soon),
        }
    except Exception as e:
        print(f"[Pending] Error: {e}")
        return JSONResponse(status_code=500, content={'success': False, 'error': 'DB_ERROR', 'message': str(e)})


@router.get("/payments-history", response_model=PaymentHistoryResponse)
async def payments_history(
    user_id: Optional[int] = None,
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
        return JSONResponse(status_code=401, content={'success': False, 'error': 'UNAUTHORIZED'})

    limit = min(max(limit, 1), 200)

    try:
        from sqlalchemy import text
        
        if user_id:
            query = """
                SELECT
                    pm.id, pm.user_id, u.email, u.company_name, u.plan,
                    pm.amount, pm.currency, pm.method, pm.reference,
                    pm.payment_date, pm.notes, pm.created_by, pm.created_at
                FROM payments_manual pm
                JOIN users u ON u.id = pm.user_id
                WHERE pm.user_id = :user_id
                ORDER BY pm.created_at DESC
                LIMIT :limit
            """
            result = db.execute(text(query), {"user_id": user_id, "limit": limit})
        else:
            query = """
                SELECT
                    pm.id, pm.user_id, u.email, u.company_name, u.plan,
                    pm.amount, pm.currency, pm.method, pm.reference,
                    pm.payment_date, pm.notes, pm.created_by, pm.created_at
                FROM payments_manual pm
                JOIN users u ON u.id = pm.user_id
                ORDER BY pm.created_at DESC
                LIMIT :limit
            """
            result = db.execute(text(query), {"limit": limit})

        rows = [dict(row._mapping) for row in result]
        for r in rows:
            for k in ('payment_date', 'created_at'):
                if r.get(k):
                    r[k] = str(r[k])

        total_amount = sum(r['amount'] for r in rows)

        return {
            'success': True,
            'payments': rows,
            'count': len(rows),
            'total_amount': round(total_amount, 2),
            'currency': 'PEN',
        }
    except Exception as e:
        print(f"[History] Error: {e}")
        return JSONResponse(status_code=500, content={'success': False, 'error': 'DB_ERROR', 'message': str(e)})
