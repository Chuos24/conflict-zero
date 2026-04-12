from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/")
async def admin_root():
    return {"message": "Admin API - En desarrollo"}
