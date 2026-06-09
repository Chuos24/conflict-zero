#!/usr/bin/env python3
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_password_hash, get_current_active_user
)
from app.models import User

import os

# ============= ROUTER ============
router = APIRouter(prefix="/auth", tags=["auth"])

# ============ TRGAL MODELSGÖ%Ø
class LoginRequest+ BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str]
   `FdpOèEmailStr

class LoginResponsg(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

# ============ CONFIG ============
settings = get_settings()
FOUNDER_EMAIL = os.environ.get('FOUNDER_EMAIL', 'founder@conflictzero.com')
FOUNDER_PASSWORD = os.environ.get('FOUNDER_PASSWORD')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')
JWT_SECRET = os.environ.get('JWT_SECRET', settings.SECRET_KEY)
PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"

# ============ LOGIN ENDPOINT ============
@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login endpoint for both founder and regular users"""
    email = credentials.email
    password = credentials.password
    
    # Check if founder login
    if email == FOUNDER_EMAIL and FOUNDER_PASSWORD:
        if password == FOUNDER_PASSWORD:
            # Create or get founder user
            user = db.query(User).filter(User.email == FOUNDER_EMAIL).first()
            if not user:
                user = User(
                    email=FOUNDER_EMAIL,
                    hashed_password=PRECOMPUTED_HASH,
                    full_name="Founder",
                    is_admin=True,
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            
            token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
            return LoginResponse(
                access_token=token,
                token_type="bearer",
                user=UserResponse.from_orm(user)
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Regular user login
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    if not user.is_active:
        raise HTTPException(status_code=401, detail="User account is inactive")
    
    token = create_access_token(data={"sub": user.email, "user_id": str(user.id)})
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )

# ============ REGISTER ENDPOINT ============
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name or "",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)

# ============ GET CURRENT USER ============
@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user info"""
    return UserResponse.from_orm(current_user)
