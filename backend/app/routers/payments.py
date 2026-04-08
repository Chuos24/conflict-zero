from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["Pagos"])

@router.get("/")
async def payments_root():
    return {"message": "Payments API - En desarrollo"}
