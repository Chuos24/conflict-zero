"""
Admin Router - User Management + Promote Endpoint
Endpoints para gestión de usuarios y promoción a admin
"""

from fastapi import APIRouter, Header, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os

# Database
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models import User

router = APIRouter(prefix="/admin", tags=["Admin"])

# Config - Load from environment
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')

# ============ MODELS ============

class UserPromoteRequest(BaseModel):
    """Request body for user promotion"""
    pass

class UserPromoteResponse(BaseModel):
    """Response after promoting user"""
    success: bool
    message: str
    user_id: str
    email: str
    is_admin: bool

# ============ MIDDLEWARE - Token Verification ============

def verify_admin_token(authorization: Optional[str] = Header(None)) -> bool:
    """Verify admin token from Authorization header"""
    if not authorization:
        return False
    
    try:
        # Format: "Bearer TOKEN"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return False
        
        token = parts[1]
        return token == ADMIN_TOKEN
    except:
        return False

# ============ ENDPOINTS ============

@router.post("/users/{user_id}/promote", response_model=UserPromoteResponse)
async def promote_user_to_admin(
    user_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Promote a user to admin status
    
    Requires:
    - Valid ADMIN_TOKEN in Authorization header: "Bearer YOUR_TOKEN"
    - Valid user_id (UUID)
    
    Returns:
    - success: True if promotion successful
    - message: Description of result
    - user details: email, is_admin status
    """
    
    # Verify admin token
    if not verify_admin_token(authorization):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized - Invalid or missing admin token"}
        )
    
    try:
        # Find user
        user = db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return JSONResponse(
                status_code=404,
                content={"detail": f"User {user_id} not found"}
            )
        
        # Promote to admin
        user.is_admin = True
        db.commit()
        db.refresh(user)
        
        return UserPromoteResponse(
            success=True,
            message=f"User {user.email} promoted to admin",
            user_id=user.id,
            email=user.email,
            is_admin=user.is_admin
        )
        
    except Exception as e:
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error promoting user: {str(e)}"}
        )

@router.get("/health")
async def admin_health():
    """Health check for admin router"""
    return {
        "status": "healthy",
        "service": "admin",
        "timestamp": datetime.utcnow().isoformat()
    }

@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Get user details (admin only)
    """
    
    # Verify admin token
    if not verify_admin_token(authorization):
        return JSONResponse(
            status_code=401,
            content={"detail": "Unauthorized"}
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        return JSONResponse(
            status_code=404,
            content={"detail": f"User {user_id} not found"}
        )
    
    return {
        "id": user.id,
        "email": user.email,
        "is_admin": user.is_admin,
        "plan": getattr(user, 'plan', 'free'),
        "created_at": user.created_at.isoformat() if hasattr(user, 'created_at') else None
    }
