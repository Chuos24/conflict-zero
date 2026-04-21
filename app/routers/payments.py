from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["Pagos"])

@router.get("/")
async def payments_root():
    """Redirect to admin payment endpoints."""
    return {
        "message": "Payments API - Use /api/v3/admin/record-payment, /api/v3/admin/activate-plan, /api/v3/admin/pending-activations, /api/v3/admin/payments-history",
        "docs": "/docs",
        "status": "active"
    }
