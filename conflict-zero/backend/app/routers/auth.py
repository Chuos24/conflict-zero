from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_password_hash, get_current_active_user
)
from app.models import User
from app.schemas import Token, UserCreate, UserResponse, LoginRequest

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Autenticación"])

@router.post(
    "/register",
    response_model=UserResponse,
    summary="Registro de Usuario",
    description="Registra un nuevo usuario en la plataforma."
)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo usuario.
    
    - **email**: Correo electrónico único
    - **password**: Contraseña (mínimo 8 caracteres)
    - **full_name**: Nombre completo
    - **company_name**: (opcional) Nombre de la empresa
    - **ruc**: (opcional) RUC de la empresa del usuario
    """
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Crear nuevo usuario
    db_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        company_name=user_data.company_name,
        ruc=user_data.ruc,
        plan_type="free",
        monthly_limit=100  # Free tier: 100 consultas/mes
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar Sesión",
    description="Autentica un usuario y retorna un token JWT."
)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Autentica un usuario con email y contraseña.
    
    Retorna un token JWT válido por 30 minutos.
    """
    # Buscar usuario
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar que el usuario esté activo
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo. Contacte soporte."
        )
    
    # Crear token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post(
    "/login/form",
    response_model=Token,
    summary="Iniciar Sesión (Form)",
    description="Endpoint compatible OAuth2 para login con formulario."
)
async def login_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Versión OAuth2 del login para integraciones."""
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Perfil de Usuario",
    description="Obtiene los datos del usuario autenticado."
)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Retorna la información del usuario actual."""
    return current_user
