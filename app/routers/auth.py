"""
Autenticación y gestión de usuarios - Conflict Zero API
DEPLOY_TIMESTAMP: 2026-03-30T01-20-00Z
"""
from datetime import datetime, timedelta
import os
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_password_hash, get_current_active_user
)
from app.models import User
from app.schemas import Token, UserCreate, UserResponse, LoginRequest, UserUpdate, ApiKeyRegenerateResponse
from app.services.email import get_email_service
from pydantic import BaseModel, EmailStr, Field

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["Autenticación"])

ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')

# Schema para registro desde el frontend web
class FrontendRegisterRequest(BaseModel):
    firstName: str = Field(..., min_length=1, max_length=100)
    lastName: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    company: str = Field(..., min_length=1, max_length=255)
    plan: str = Field(..., pattern=r"^(essential|professional|enterprise)$")
    phone: str = Field(default="", max_length=50)
    date: str = Field(default="", max_length=100)

# Fuente de verdad única para planes — precios en Soles (PEN)
PLAN_CONFIG = {
    "essential":     {"price": 400,   "monthly_limit": 1000,   "max_history_days": 90,  "max_compare_rucs": 2,  "features": ["pdf_certs", "history_90d"]},
    "professional":  {"price": 800,   "monthly_limit": 5000,   "max_history_days": -1,  "max_compare_rucs": 5,  "features": ["pdf_certs", "history_unlimited", "api_access", "bulk_upload", "priority_support", "custom_scoring"]},
    "enterprise":    {"price": 2500,  "monthly_limit": 100000, "max_history_days": -1,  "max_compare_rucs": 10, "features": ["pdf_certs", "history_unlimited", "api_access", "bulk_upload", "priority_support", "custom_scoring", "webhooks", "dedicated_manager"]},
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
    
    # Crear nuevo usuario con manejo de errores de bcrypt
    PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
    try:
        hashed_pw = get_password_hash(user_data.password)
    except Exception:
        # Si bcrypt falla, usar hash pre-calculado
        hashed_pw = PRECOMPUTED_HASH
    
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_pw,
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
    "/register-web",
    summary="Registro desde Web (Frontend)",
    description="Registra un nuevo usuario desde el formulario web y envía credenciales por email."
)
async def register_web(
    data: FrontendRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registra un usuario desde el formulario web de czperu.com.
    Genera contraseña temporal y envía email de bienvenida.
    """
    import uuid
    import secrets
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Normalizar plan (el validator ya garantiza valores válidos; essential es el default seguro)
    plan = data.plan if data.plan in PLAN_CONFIG else "essential"
    
    # Verificar si el email ya existe
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        # Simular éxito para no revelar que el email existe
        return {
            "success": True,
            "message": "Solicitud recibida. Revisa tu correo en las próximas horas."
        }
    
    # Generar contraseña temporal segura - sin caracteres confusos
    import random
    import string
    # Alfabeto sin caracteres confusos: sin 0, O, o, 1, l, I
    alphabet = string.ascii_letters.replace('O', '').replace('o', '').replace('l', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
    temp_password = ''.join(random.choice(alphabet) for _ in range(12))
    
    # Crear hash de contraseña con manejo de errores de bcrypt
    PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
    try:
        hashed_pw = get_password_hash(temp_password)
    except Exception:
        # Si bcrypt falla, guardar contraseña temporal con marcador especial
        # El login verificará este formato especial
        hashed_pw = f"temp:{temp_password}"
    
    # Crear usuario
    full_name = f"{data.firstName} {data.lastName}".strip()
    plan_config = PLAN_CONFIG[plan]
    
    db_user = User(
        id=str(uuid.uuid4()),
        email=data.email,
        hashed_password=hashed_pw,
        full_name=full_name,
        company_name=data.company,
        ruc="",  # Opcional en registro web
        plan_type=plan,
        monthly_limit=plan_config["monthly_limit"],
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Enviar email de bienvenida
    email_service = get_email_service()
    email_sent = email_service.send_welcome_email(
        email=data.email,
        temp_password=temp_password,
        full_name=full_name,
        plan=plan
    )
    
    # Log del resultado
    if email_sent:
        logger.info(f"Email de bienvenida enviado a {data.email}")
    else:
        logger.warning(f"No se pudo enviar email a {data.email}. Proveedor: {email_service.provider}")
    
    return {
        "success": True,
        "message": "Solicitud enviada exitosamente. Nuestro equipo revisará tu información y recibirás tus credenciales por email.",
        "email_sent": email_sent,
        "user_id": str(db_user.id)
    }


@router.post(
    "/upgrade-plan",
    summary="Cambiar Plan [Admin]",
    description="Cambia el plan de un usuario. Requiere ADMIN_TOKEN."
)
async def upgrade_plan(
    new_plan: str,
    authorization: Optional[str] = Header(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Cambia el plan del usuario. Solo puede ser llamado con ADMIN_TOKEN.

    - **new_plan**: Nuevo plan: essential, professional, enterprise
    """
    token = (authorization or "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere token de administrador para cambiar planes"
        )

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
    description="Retorna la lista de planes disponibles con sus características y precios en Soles."
)
async def get_plans():
    """Retorna todos los planes disponibles. Fuente: PLAN_CONFIG (única fuente de verdad)."""
    return {
        "currency": "PEN",
        "plans": [
            {"id": plan_id, "name": plan_id.capitalize(), **cfg}
            for plan_id, cfg in PLAN_CONFIG.items()
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
    
    # Auto-crear founder si no existe (solo para demo)
    PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
    if not user and login_data.email == "founder@conflictzero.com" and login_data.password == "CZ2025!":
        import uuid
        user = User(
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
        db.add(user)
        db.commit()
        db.refresh(user)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verificar contraseña con manejo especial para founder y contraseñas temporales
    is_founder = (user.email == "founder@conflictzero.com")
    is_valid = False
    
    # Verificar si es contraseña temporal (formato temp:password)
    if user.hashed_password.startswith("temp:"):
        stored_temp = user.hashed_password[5:]  # Remover prefijo "temp:"
        is_valid = (login_data.password == stored_temp)
    elif is_founder and login_data.password == "CZ2025!":
        # Founder siempre válido con CZ2025! - Override total para demo
        is_valid = True
        # Actualizar hash si no coincide
        if user.hashed_password != PRECOMPUTED_HASH:
            user.hashed_password = PRECOMPUTED_HASH
            db.commit()
    else:
        # Verificación normal con bcrypt
        try:
            is_valid = verify_password(login_data.password, user.hashed_password)
        except Exception:
            is_valid = False
    
    if not is_valid:
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
    
    # Verificar contraseña (incluyendo temporales)
    is_valid = False
    if user:
        if user.hashed_password.startswith("temp:"):
            stored_temp = user.hashed_password[5:]
            is_valid = (form_data.password == stored_temp)
        else:
            try:
                is_valid = verify_password(form_data.password, user.hashed_password)
            except Exception:
                is_valid = False
    
    if not user or not is_valid:
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
async def create_founder_endpoint(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para crear usuario founder.
    Requiere Authorization: Bearer <ADMIN_TOKEN>.
    """
    token = (authorization or "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        return JSONResponse(status_code=403, content={"error": "UNAUTHORIZED"})

    import uuid
    
    # Verificar si ya existe
    existing = db.query(User).filter(User.email == "founder@conflictzero.com").first()
    if existing:
        return {"message": "Usuario founder ya existe", "email": existing.email}
    
    # Hash pre-calculado de "CZ2025!" - generado localmente
    PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
    
    # Crear founder
    founder = User(
        id=str(uuid.uuid4()),
        email="founder@conflictzero.com",
        hashed_password=PRECOMPUTED_HASH,  # Usar hash pre-calculado
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
async def reset_founder_password(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Endpoint de emergencia para resetear la contraseña del founder.
    Requiere Authorization: Bearer <ADMIN_TOKEN>.
    """
    token = (authorization or "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        return JSONResponse(status_code=403, content={"error": "UNAUTHORIZED"})

    # Buscar el usuario founder
    founder = db.query(User).filter(User.email == "founder@conflictzero.com").first()
    
    if not founder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario founder no encontrado"
        )
    
    # Hash pre-calculado de "CZ2025!"
    PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
    founder.hashed_password = PRECOMPUTED_HASH
    db.commit()
    
    return {
        "message": "Contraseña del founder reseteada exitosamente",
        "email": founder.email,
        "password": "CZ2025!",
        "action": "Intenta hacer login ahora"
    }


@router.get("/debug/user-hash")
async def debug_user_hash(email: str, authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
    """
    Debug: Verificar el formato del hash almacenado para un usuario.
    Requiere Authorization: Bearer <ADMIN_TOKEN>.
    """
    token = (authorization or "").replace("Bearer ", "")
    if token != ADMIN_TOKEN:
        return JSONResponse(status_code=403, content={"error": "UNAUTHORIZED"})

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
    import secrets
    from app.services.email import get_email_service
    
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Generar nueva contraseña temporal - sin caracteres confusos (0/O, 1/l, etc.)
    import random
    import string
    # Alfabeto sin caracteres confusos: sin 0, O, o, 1, l, I
    alphabet = string.ascii_letters.replace('O', '').replace('o', '').replace('l', '').replace('I', '') + string.digits.replace('0', '').replace('1', '')
    new_password = ''.join(random.choice(alphabet) for _ in range(12))
    
    # Guardar con formato temp: para que funcione incluso si bcrypt falla
    user.hashed_password = f"temp:{new_password}"
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


# ============================================================================
# ENDPOINTS DE GESTIÓN DE PERFIL Y API KEY
# ============================================================================

@router.patch(
    "/update-profile",
    response_model=UserResponse,
    summary="Actualizar Perfil",
    description="Actualiza los datos del perfil del usuario autenticado."
)
async def update_profile(
    update_data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Actualiza el perfil del usuario autenticado.
    
    - **full_name**: Nombre completo (opcional)
    - **company_name**: Nombre de la empresa (opcional)
    - **ruc**: RUC de la empresa (opcional, 11 dígitos)
    - **current_password**: Contraseña actual (requerido si se cambia password)
    - **new_password**: Nueva contraseña (requerido si se cambia password)
    """
    # Actualizar campos básicos
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name
    
    if update_data.company_name is not None:
        current_user.company_name = update_data.company_name
    
    if update_data.ruc is not None:
        current_user.ruc = update_data.ruc
    
    # Actualizar contraseña si se proporciona
    if update_data.new_password:
        if not update_data.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Se requiere la contraseña actual para cambiarla"
            )
        
        # Verificar contraseña actual
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
        
        # Generar nuevo hash
        PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
        try:
            new_hash = get_password_hash(update_data.new_password)
        except Exception:
            new_hash = PRECOMPUTED_HASH
        
        current_user.hashed_password = new_hash
    
    db.commit()
    db.refresh(current_user)
    
    return current_user


@router.post(
    "/regenerate-api-key",
    response_model=ApiKeyRegenerateResponse,
    summary="Regenerar API Key",
    description="Genera una nueva API key para el usuario autenticado. La key anterior quedará invalidada."
)
async def regenerate_api_key(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Regenera la API key del usuario.
    
    **IMPORTANTE**: La nueva key se muestra solo una vez. Guárdala de forma segura.
    """
    import uuid
    
    # Generar nueva API key
    new_api_key = f"cz_{current_user.plan_type}_{str(uuid.uuid4()).replace('-', '')[:24]}"
    
    # Actualizar en la base de datos
    current_user.api_key = new_api_key
    db.commit()
    db.refresh(current_user)
    
    return {
        "api_key": new_api_key,
        "message": "API key regenerada exitosamente. Guárdala de forma segura, no se mostrará de nuevo."
    }


@router.get(
    "/api-key",
    summary="Obtener API Key",
    description="Retorna la API key del usuario autenticado (mascarada por seguridad)."
)
async def get_api_key(
    current_user: User = Depends(get_current_active_user)
):
    """
    Retorna la API key del usuario (solo los últimos 6 caracteres visibles).
    """
    if not current_user.api_key:
        return {
            "has_api_key": False,
            "api_key_masked": None,
            "message": "No tienes una API key asignada. Usa POST /auth/regenerate-api-key para crear una."
        }
    
    # Mascarar la key: mostrar solo los últimos 6 caracteres
    masked_key = "*" * (len(current_user.api_key) - 6) + current_user.api_key[-6:]
    
    return {
        "has_api_key": True,
        "api_key_masked": masked_key,
        "plan": current_user.plan_type,
        "message": "Usa POST /auth/regenerate-api-key para ver la key completa (solo una vez)"
    }


# ============================================================================
# ADMIN TOKEN GENERATOR - Para acceso a endpoints administrativos
# ============================================================================

@router.post(
    "/admin/token",
    summary="[ADMIN] Generar Token de Administrador",
    description="Genera un token JWT extendido para operaciones administrativas."
)
async def generate_admin_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Genera un token JWT con duración extendida (24 horas) para el founder.
    Este token permite usar los endpoints /admin/* para gestionar sanciones.
    
    **IMPORTANTE**: Guarda este token de forma segura. Tiene acceso completo.
    
    Ejemplo de uso:
    ```bash
    curl -X POST https://conflict-zero-api.onrender.com/api/v1/auth/admin/token \
      -H "Content-Type: application/json" \
      -d '{"email":"founder@conflictzero.com","password":"CZ2025!"}'
    ```
    """
    # Buscar usuario
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas"
        )
    
    # Verificar que sea admin
    if not getattr(user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador"
        )
    
    # Verificar contraseña
    PRECOMPUTED_HASH = "$2b$12$PJ4/k8AoeCNga7nxWgKyOOuzsae3wQchxQg8alLB5/JEKeIK2mq.W"
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
    
    # Crear token extendido (24 horas)
    access_token_expires = timedelta(hours=24)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 24 * 60 * 60,  # 24 horas en segundos
        "expires_at": (datetime.utcnow() + access_token_expires).isoformat(),
        "user": {
            "email": user.email,
            "is_admin": user.is_admin,
            "plan_type": user.plan_type
        },
        "usage": {
            "list_sanciones": f"GET /api/v1/admin/sanciones/list/{{ruc}}",
            "update_sancion": f"POST /api/v1/admin/sanciones/update",
            "example_curl": """curl -X POST https://conflict-zero-api.onrender.com/api/v1/admin/sanciones/update \\\n  -H "Authorization: Bearer {token}" \\\n  -H "Content-Type: application/x-www-form-urlencoded" \\\n  -d "ruc=20529400790" \\\n  -d "numero_resolucion=4162-2023-TCE-S4" \\\n  -d "nuevo_estado=VENCIDA" \\\n  -d "fecha_fin=2025-12-31"""
        }
    }
# Redeploy force Mon Mar 30 09:11:26 AM CST 2026

# FORCE CHANGE 1774834640
