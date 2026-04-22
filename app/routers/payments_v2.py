"""
Payments Router v2 — Conflict Zero
Integración con Culqi para cobros automáticos de planes.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user, verify_token
from app.models import User, PaymentManual
from app.services.culqi_service import culqi_service, PLAN_PRICES_CENTS, PLAN_NAMES

router = APIRouter(prefix="/payments", tags=["Pagos"])


# ─── Schemas ────────────────────────────────────────────────────────────────

from pydantic import BaseModel

class CulqiChargeRequest(BaseModel):
    token: str                    # Token generado por Culqi.js
    plan: str                     # essential | professional | enterprise
    email: Optional[str] = None   # Si no se envía, usa el del usuario autenticado


class CulqiConfigResponse(BaseModel):
    enabled: bool
    public_key: Optional[str]
    currency: str
    plans: dict


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/config", response_model=CulqiConfigResponse)
async def get_payment_config():
    """
    Devuelve la configuración de Culqi para el frontend.
    Incluye la public key y precios de planes.
    """
    config = culqi_service.get_plan_config()
    return {
        "enabled": culqi_service.is_configured(),
        "public_key": config.get("public_key"),
        "currency": config.get("currency"),
        "plans": config.get("plans"),
    }


@router.post("/charge")
async def create_charge(
    body: CulqiChargeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Procesa un pago con Culqi usando el token del frontend.
    Crea el cargo y registra el pago en la base de datos.
    """
    if not culqi_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Pasarela de pagos no configurada. Contacte a soporte."
        )

    # Validar plan
    if body.plan not in PLAN_PRICES_CENTS:
        raise HTTPException(
            status_code=400,
            detail=f"Plan no válido. Opciones: {list(PLAN_PRICES_CENTS.keys())}"
        )

    amount = PLAN_PRICES_CENTS[body.plan]
    email = body.email or current_user.email

    # Crear cargo en Culqi
    result = culqi_service.create_charge(
        token=body.token,
        amount=amount,
        currency="PEN",
        email=email,
        description=f"Plan {PLAN_NAMES[body.plan]} — Conflict Zero",
        metadata={
            "user_id": str(current_user.id),
            "plan": body.plan,
            "platform": "conflict_zero_web",
        },
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": result.get("error", "Error en procesamiento"),
                "type": result.get("error_type", "unknown"),
            }
        )

    # Registrar pago en DB (tabla PaymentManual como registro genérico)
    payment = PaymentManual(
        user_id=current_user.id,
        amount=amount / 100,  # Convertir a soles
        currency="PEN",
        method="culqi_card",
        reference=result["charge_id"],
        notes=f"Culqi charge: {result.get('status')} — Plan {body.plan}",
        payment_date=datetime.utcnow(),
    )
    db.add(payment)

    # Activar plan automáticamente si el cargo fue exitoso
    if result.get("status") == "captured":
        current_user.plan_type = body.plan
        # Resetear contador mensual
        current_user.monthly_requests = 0

    db.commit()
    db.refresh(payment)

    return {
        "success": True,
        "charge_id": result["charge_id"],
        "status": result.get("status"),
        "amount": amount / 100,
        "currency": "PEN",
        "plan": body.plan,
        "receipt_url": result.get("receipt_url"),
        "payment_id": payment.id,
    }


@router.get("/history")
async def get_my_payments(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Historial de pagos del usuario autenticado.
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
        "plan_type": user.plan_type,
        "payments": [
            {
                "id": p.id,
                "amount": p.amount,
                "currency": p.currency,
                "method": p.method,
                "reference": p.reference,
                "notes": p.notes,
                "payment_date": p.payment_date.isoformat() if p.payment_date else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in payments
        ],
        "count": len(payments),
    }


@router.post("/webhook/culqi")
async def culqi_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Webhook para eventos de Culqi (charge.created, charge.captured, etc.)
    Actualiza el estado del pago en la base de datos.
    """
    body = await request.body()
    headers = dict(request.headers)
    signature = headers.get("x-culqi-signature", "")

    # Validar firma
    if culqi_service.is_configured() and not culqi_service.validate_webhook(headers, body.decode(), signature):
        raise HTTPException(status_code=401, detail="Firma inválida")

    try:
        import json
        data = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="JSON inválido")

    event_type = data.get("object", "")
    charge = data.get("data", {})
    charge_id = charge.get("id")
    metadata = charge.get("metadata", {})
    user_id = metadata.get("user_id")
    plan = metadata.get("plan")
    status = charge.get("status")

    # Buscar pago por charge_id
    payment = db.query(PaymentManual).filter(
        PaymentManual.reference == charge_id
    ).first()

    if payment:
        payment.notes = f"Culqi webhook: {status} — {event_type}"
        db.commit()

    # Si es captured y tenemos user_id, activar plan
    if status == "captured" and user_id and plan:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.plan_type = plan
            user.monthly_requests = 0
            db.commit()

    return {"success": True, "event": event_type, "charge_id": charge_id}
