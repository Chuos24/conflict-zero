from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
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

# Configuración de planes - UHNW: Solo planes pagos
PLAN_CONFIG = {
    "essential": {"monthly_limit": 1000, "features": ["pdf_certs", "history_90d"]},
    "professional": {"monthly_limit": 5000, "features": ["pdf_certs", "history_unlimited", "api_access", "bulk_upload", "priority_support", "custom_scoring"]},
    "enterprise": {"monthly_limit": 100000, "features": ["pdf_certs", "history_unlimited", "api_access", "bulk_upload", "priority_support", "custom_scoring", "webhooks", "dedicated_manager"]}
}

@router.post(
    "/register",
    response_model=UserResponse,
    summary="Registro de Usuario",
    description="Registra un nuevo usuario en la plataforma."
)
async def register(
    user_data: UserCreate,
    plan: str = Query(default="essential", description="Plan seleccionado: essential, professional, enterprise"),
    db: Session = Depends(get_db)
):
    """
    Registra un nuevo usuario.
    
    - **email**: Correo electrónico único
    - **password**: Contraseña (mínimo 8 caracteres)
    - **full_name**: Nombre completo
    - **company_name**: (opcional) Nombre de la empresa
    - **ruc**: (opcional) RUC de la empresa del usuario
    - **plan**: (query param) Plan seleccionado: essential, professional, enterprise
    """
    # Validar plan
    if plan not in PLAN_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan no válido. Opciones: {', '.join(PLAN_CONFIG.keys())}"
        )
    
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo electrónico ya está registrado"
        )
    
    # Obtener configuración del plan
    plan_config = PLAN_CONFIG[plan]
    
    # Crear nuevo usuario
    db_user = User(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        company_name=user_data.company_name,
        ruc=user_data.ruc,
        plan_type=plan,
        monthly_limit=plan_config["monthly_limit"]
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

@router.post(
    "/upgrade-plan",
    summary="Cambiar Plan",
    description="Permite al usuario cambiar su plan actual."
)
async def upgrade_plan(
    new_plan: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cambia el plan del usuario.
    
    - **new_plan**: Nuevo plan: essential, professional, enterprise
    """
    if new_plan not in PLAN_CONFIG:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan no válido. Opciones: {', '.join(PLAN_CONFIG.keys())}"
        )
    
    # Actualizar plan
    plan_config = PLAN_CONFIG[new_plan]
    current_user.plan_type = new_plan
    current_user.monthly_limit = plan_config["monthly_limit"]
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": f"Plan actualizado a {new_plan}",
        "plan_type": current_user.plan_type,
        "monthly_limit": current_user.monthly_limit,
        "features": plan_config["features"]
    }

@router.get(
    "/plans",
    summary="Ver Planes Disponibles",
    description="Retorna la lista de planes disponibles con sus características."
)
async def get_plans():
    """Retorna todos los planes disponibles."""
    return {
        "plans": [
            {
                "id": "essential",
                "name": "Essential",
                "price": 400,
                "monthly_limit": 1000,
                "max_history_days": 90,
                "max_compare_rucs": 2,
                "features": ["pdf_certs", "history_90d"]
            },
            {
                "id": "professional",
                "name": "Professional",
                "price": 800,
                "monthly_limit": 5000,
                "max_history_days": -1,
                "max_compare_rucs": 5,
                "features": ["pdf_certs", "history_unlimited", "api_access", "bulk_upload", "priority_support", "custom_scoring"]
            },
            {
                "id": "enterprise",
                "name": "Enterprise",
                "price": 2500,
                "monthly_limit": 100000,
                "max_history_days": -1,
                "max_compare_rucs": 10,
                "features": ["pdf_certs", "history_unlimited", "api_access", "bulk_upload", "priority_support", "custom_scoring", "webhooks", "dedicated_manager"]
            }
        ]
    }

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


@router.api_route("/setup/create-founder", methods=["GET", "POST"])
async def create_founder_endpoint(db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para crear usuario founder.
    Solo funciona si no existe ningún usuario founder.
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
        hashed_password=get_password_hash("FounderPass2025!"),
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
        "password": "FounderPass2025!"
    }


@router.api_route("/setup/reset-founder-password", methods=["GET", "POST"])
async def reset_founder_password(db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para resetear la contraseña del founder.
    Útil si hay problemas con bcrypt.
    """
    # Buscar el usuario founder
    founder = db.query(User).filter(User.email == "founder@conflictzero.com").first()
    
    if not founder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario founder no encontrado"
        )
    
    # Resetear contraseña
    founder.hashed_password = get_password_hash("FounderPass2025!")
    db.commit()
    
    return {
        "message": "Contraseña del founder reseteada exitosamente",
        "email": founder.email,
        "password": "FounderPass2025!",
        "action": "Intenta hacer login ahora"
    }
