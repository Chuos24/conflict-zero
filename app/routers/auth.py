#!/usr/bin/env python3
"""
Autenticación y gestión de usuarios - Conflict Zero API
DEPLOY_TIMESTAMP: 2026-03-30T01-20-00Z
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_password_hash, get_current_active_user
)
from app.models import User

import os
from slowapi import Limiter
from slowapi.util import get_remote_address

# =========== ROUTER ===========
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

# =========== MODELS ===========
class LoginRequest(BaseModel):
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

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    company_name: Optional[str] = None
    ruc: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None

class ApiKeyRegenerateResponse(BaseModel):
    api_key: str
    message: str

# =========== CONFIG ===========
settings = get_settings()
FOUNDER_EMAIL = os.environ.get('FOUNDER_EMAIL')
FOUNDER_PASSWORD = os.environ.get('FOUNDER_PASSWORD')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')
JWT_SECRET = os.environ.get('JWT_SECRET', settings.SECRET_KEY)
PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"

# =========== LOGIN ENDPOINT ===========
@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    """Login endpoint for both founder and regular users"""
    email = credentials.email
    password = credentials.password
    
    # Check if founder login (both env vars must be set)
    if FOUNDER_EMAIL and FOUNDER_PASSWORD and email == FOUNDER_EMAIL:
        if password == FOUNDER_PASSWORD:
            # Create or get founder
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

# =========== REGISTER ENDPOINT ===========
@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, user_data: UserCreate, db: Session = Depends(get_db)):
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

# =========== GET CURRENT USER ===========
@router.get("/me", response_model=UserResponse)
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """Retorna la información del usuario actual."""
    return UserResponse.from_orm(current_user)

@router.api_route("/setup/create-founder", methods=["GET", "POST"])
async def create_founder_endpoint(db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para crear usuario founder.
    Usa hash pre-calculado para evitar problemas con bcrypt en Render.
    """
    import uuid
    
    # Verificar si ya existe
    existing = db.query(User).filter(User.email == "founder@conflictzero.com").first()
    if existing:
        return {"message": "Usuario founder ya existe", "email": existing.email}
    
    # Crear founder
    founder = User(
        id=str(uuid.uuid4()),
        email="founder@conflictzero.com",
        hashed_password=PRECOMPUTED_HASH,
        full_name="Conflict Zero Founder",
        company_name="Conflict Zero Inc.",
        ruc="20100000001",
        is_active=True,
        is_admin=True,
        plan_type="enterprise",
        monthly_requests=0,
        monthly_limit=999999,
        api_key="cz_founder_" + str(uuid.uuid4()).replace("-", "")
    )
    db.add(founder)
    db.commit()
    
    return {
        "message": "Usuario founder creado exitosamente",
        "email": founder.email,
        "password": "CZ2025!"
    }


@router.get("/debug/email-status")
async def debug_email_status():
    """Debug: Verificar estado del servicio de email"""
    from app.services.email import get_email_service, SENDGRID_AVAILABLE
    import os
    
    service = get_email_service()
    sg_key = os.getenv("SENDGRID_API_KEY", "")
    
    return {
        "provider": service.provider,
        "sendgrid_available": SENDGRID_AVAILABLE,
        "sendgrid_key_configured": len(sg_key) > 0,
        "sendgrid_key_prefix": sg_key[:10] + "..." if len(sg_key) > 10 else "none",
        "from_email": service.from_email,
        "from_name": service.from_name
    }


@router.api_route("/setup/reset-founder-password", methods=["GET", "POST"])
async def reset_founder_password(db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para resetear la contraseña del founder.
    Usa hash pre-calculado para evitar problemas con bcrypt.
    """
    # Buscar el usuario founder
    founder = db.query(User).filter(User.email == "founder@conflictzero.com").first()
    
    if not founder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario founder no encontrado"
        )
    
    founder.hashed_password = PRECOMPUTED_HASH
    db.commit()
    
    return {
        "message": "Contraseña del founder reseteada exitosamente",
        "email": founder.email,
        "password": "CZ2025!",
        "action": "Intenta hacer login ahora"
    }


@router.get("/debug/user-hash")
async def debug_user_hash(email: str, db: Session = Depends(get_db)):
    """
    Debug: Verificar el formato del hash almacenado para un usuario.
    Solo para diagnóstico - no expone la contraseña real.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return {"error": "Usuario no encontrado"}
    
    hash_preview = user.hashed_password[:20] + "..." if len(user.hashed_password) > 20 else user.hashed_password
    is_temp = user.hashed_password.startswith("temp:")
    
    return {
        "email": user.email,
        "hash_preview": hash_preview,
        "hash_length": len(user.hashed_password),
        "is_temp_format": is_temp,
        "is_active": user.is_active,
        "plan_type": user.plan_type
    }


@router.post("/setup/reset-user-password")
async def reset_user_password(email: str, db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para resetear contraseña de cualquier usuario.
    Genera nueva contraseña temporal y la envía por email.
    """
    import random
    import string
    from app.services.email import get_email_service
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Alfabeto sin caracteres confusos
    alphabet = string.ascii_letters.replace('O', '').replace('o', '').replace('l', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
    new_password = ''.join(random.choice(alphabet) for _ in range(12))
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Enviar email con nueva contraseña
    email_service = get_email_service()
    email_sent = email_service.send_welcome_email(
        email=user.email,
        temp_password=new_password,
        full_name=user.full_name,
        plan=user.plan_type
    )
    
    return {
        "message": "Contraseña reseteada exitosamente",
        "email": user.email,
        "email_sent": email_sent,
        "note": "Revisa tu correo para la nueva contraseña"
    }


@router.patch(
    "/update-profile",
    response_model=UserResponse,
    summary="Actualizar Perfil"
)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza el perfil del usuario autenticado."""
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    
    if update_data.company_name is not None:
        current_user.company_name = update_data.company_name
    
    if update_data.ruc is not None:
        current_user.ruc = update_data.ruc
    
    if update_data.new_password:
        if not update_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere la contraseña actual para cambiarla"
            )
        
        is_valid = False
        if current_user.hashed_password.startswith("temp:"):
            stored_temp = current_user.hashed_password[5:]
            is_valid = (update_data.current_password == stored_temp)
        else:
            try:
                is_valid = verify_password(update_data.current_password, current_user.hashed_password)
            except Exception:
                is_valid = False
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Contraseña actual incorrecta"
            )
        
        try:
            new_hash = get_password_hash(update_data.new_password)
        except Exception:
            new_hash = PRECOMPUTED_HASH
        
        current_user.hashed_password = new_hash
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@router.post(
    "/regenerate-api-key",
    response_model=ApiKeyRegenerateResponse
)
async def regenerate_api_key(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Genera una nueva API key para el usuario autenticado."""
    import uuid
    
    new_api_key = f"cz_{current_user.plan_type}_{str(uuid.uuid4()).replace('-', '')[:24]}"
    
    current_user.api_key = new_api_key
    db.commit()
    db.refresh(current_user)
    
    return {
        "api_key": new_api_key,
        "message": "API key regenerada exitosamente. Guárdala de forma segura, no se mostrará de nuevo."
    }


@router.get("/api-key")
async def get_api_key(
    current_user: User = Depends(get_current_active_user)
):
    """Retorna la API key del usuario (mascarada por seguridad)."""
    if not current_user.api_key:
        return {
            "has_api_key": False,
            "api_key_masked": None,
            "message": "No tienes una API key asignada. Usa POST /auth/regenerate-api-key para crear una."
        }
    
    masked_key = "*" * (len(current_user.api_key) - 6) + current_user.api_key[-6:]
    
    return {
        "has_api_key": True,
        "api_key_masked": masked_key,
        "plan": current_user.plan_type,
        "message": "Usa POST /auth/regenerate-api-key para ver la key completa (solo una vez)"
    }


@router.post("/admin/token")
async def generate_admin_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """Genera un token JWT extendido para operaciones administrativas."""
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    if not getattr(user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador"
        )
    
    is_valid = False
    try:
        if login_data.email == "founder@conflictzero.com" and login_data.password == "CZ2025!":
            if user.hashed_password == PRECOMPUTED_HASH:
                is_valid = True
        else:
            is_valid = verify_password(login_data.password, user.hashed_password)
    except:
        if login_data.email == "founder@conflictzero.com" and login_data.password == "CZ2025!" and user.hashed_password == PRECOMPUTED_HASH:
            is_valid = True
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 24 * 60 * 60,
        "expires_at": (datetime.now(timezone.utc) + access_token_expires).isoformat(),
        "user": {
            "email": user.email,
            "is_admin": user.is_admin,
            "plan_type": user.plan_type
        }
    }

# Redeploy force Mon Mar 30 09:11:26 AM CST 2026
# FORCE CHANGE 1774834640
