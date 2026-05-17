from fastapi import APIRouter, Depends, HTTPException, status
from app.core.rate_limit import rate_limit_dependency
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/payments", tags=["Pagos"])

@router.get("/")
async def payments_root():
    return {"message": "Payments API - En desarrollo"}

@router.get(
    "/plans",
    summary="Planes de Pago",
    description="Retorna los planes disponibles para suscripción."
)
async def get_payment_plans():
    return {
        "plans": [
            {"id": "essential", "name": "Essential", "price": 400, "currency": "PEN", "monthly_limit": 1000},
            {"id": "professional", "name": "Professional", "price": 800, "currency": "PEN", "monthly_limit": 5000},
            {"id": "enterprise", "name": "Enterprise", "price": 2500, "currency": "PEN", "monthly_limit": 100000}
        ]
    }

@router.post(
    "/create-subscription",
    summary="Crear Suscripción",
    description="Inicia una suscripción para el usuario autenticado."
)
async def create_subscription(
    plan_id: str,
    current_user: User = Depends(get_current_active_user),
    rate_limit: dict = Depends(rate_limit_dependency)
):
    valid_plans = ["essential", "professional", "enterprise"]
    if plan_id not in valid_plans:
        raise HTTPException(status_code=400, detail="Plan no válido")
    return {
        "status": "pending",
        "plan": plan_id,
        "user_id": str(current_user.id),
        "message": "Suscripción registrada. Integración con pasarela de pago pendiente."
    }
