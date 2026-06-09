from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import os
from app.db import get_db
from app.models import User
from app.core.config import ADMIN_TOKEN

router = APIRouter(prefix="/admin", tags=["admin"])

@router.post("/users/{user_id}/promote")
async def promote_user(user_id: str, token: str = Query(...), db: Session = Depends(get_db)):
    """Promote user to admin."""
    if token != os.environ.get('ADMIN_TOKEN', ADMIN_TOKEN):
        raise HTTPException(401, "Invalid token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_admin = True
    db.commit()
    return {"success": True, "email": user.email, "is_admin": True}
