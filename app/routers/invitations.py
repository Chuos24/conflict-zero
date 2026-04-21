"""
Invitations Router - Conflict Zero API
Ported from api_v3.py (Backend B) to Backend A modular structure
Sistema de invitaciones para Mi Red (Professional/Enterprise)
"""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field, EmailStr

from app.core.database import get_db
from app.core.security import verify_token
from app.models import User, Invitation

router = APIRouter(prefix="/invitations", tags=["Invitaciones"])

# ============================================================================
# Schemas
# ============================================================================

class CreateInvitationRequest(BaseModel):
    email: EmailStr
    ruc_invitado: Optional[str] = Field(None, min_length=11, max_length=11)

class RegisterWithInvitationRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    company_name: Optional[str] = None
    ruc: str = Field(..., min_length=11, max_length=11)
    token: str


# ============================================================================
# Helpers
# ============================================================================

def get_current_user(authorization: Optional[str]) -> Optional[dict]:
    """Obtener usuario actual desde JWT en header Authorization."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "")
    return verify_token(token)


def generate_invitation_token() -> str:
    """Genera token único para invitación."""
    return secrets.token_urlsafe(32)


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/")
async def create_invitation(
    request: CreateInvitationRequest,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Crear invitación para subcontratista.
    Requiere plan Professional o Enterprise.
    """
    user_payload = get_current_user(authorization)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Token requerido")
    
    # Obtener usuario completo
    user = db.query(User).filter(User.id == user_payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Verificar plan
    if user.plan_type not in ["professional", "enterprise"]:
        raise HTTPException(
            status_code=403,
            detail="Invitaciones requieren plan Professional o Enterprise"
        )
    
    # Generar token único
    token = generate_invitation_token()
    
    # Crear invitación (expira en 24h)
    invitation = Invitation(
        invitador_ruc=user.ruc or "00000000000",
        email=request.email,
        token=token,
        ruc_invitado=request.ruc_invitado,
        expira=datetime.utcnow() + timedelta(hours=24)
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    register_link = f"https://czperu.com/registro?invitador={user.ruc}&token={token}"
    
    return {
        "success": True,
        "invitation": {
            "id": invitation.id,
            "email": request.email,
            "token": invitation.token,
            "expira": invitation.expira.isoformat() if invitation.expira else None,
            "created_at": invitation.created_at.isoformat() if invitation.created_at else None,
            "register_link": register_link
        },
        "message": f"Invitación creada. Link: {register_link}"
    }


@router.get("/validate")
async def validate_invitation(
    token: str,
    db: Session = Depends(get_db)
):
    """
    Validar token de invitación.
    Retorna info del invitador si es válido.
    """
    invitation = db.query(Invitation).filter(
        Invitation.token == token,
        Invitation.usada == False,
        Invitation.expira > datetime.utcnow()
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    # Buscar info del invitador
    invitador = db.query(User).filter(User.ruc == invitation.invitador_ruc).first()
    
    return {
        "success": True,
        "valid": True,
        "invitador": {
            "ruc": invitation.invitador_ruc,
            "company_name": invitador.company_name if invitador else invitation.invitador_ruc
        },
        "email": invitation.email,
        "expira": invitation.expira.isoformat() if invitation.expira else None
    }


@router.post("/register")
async def register_with_invitation(
    request: RegisterWithInvitationRequest,
    db: Session = Depends(get_db)
):
    """
    Registrar usuario con invitación.
    """
    # Validar token
    invitation = db.query(Invitation).filter(
        Invitation.token == request.token,
        Invitation.usada == False,
        Invitation.expira > datetime.utcnow()
    ).first()
    
    if not invitation:
        raise HTTPException(status_code=400, detail="Token inválido o expirado")
    
    # Validar email coincida
    if invitation.email.lower() != request.email.lower():
        raise HTTPException(status_code=400, detail="El email no coincide con la invitación")
    
    # Verificar email único
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="El email ya está registrado")
    
    from app.core.security import get_password_hash
    
    # Crear usuario
    user = User(
        email=request.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        company_name=request.company_name or f"Empresa {request.ruc}",
        ruc=request.ruc,
        is_active=True,
        plan_type="essential",
        status="active"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Marcar invitación como usada
    invitation.usada = True
    invitation.usada_por = user.id
    db.commit()
    
    # Crear JWT
    from app.core.security import create_access_token
    token_jwt = create_access_token(data={"sub": user.id})
    
    return {
        "success": True,
        "message": "Usuario registrado exitosamente",
        "token": token_jwt,
        "user": {
            "id": user.id,
            "email": user.email,
            "ruc": user.ruc,
            "company_name": user.company_name,
            "invitado_por": invitation.invitador_ruc
        },
        "invitador": {
            "ruc": invitation.invitador_ruc
        }
    }


@router.get("/mis-invitados")
async def get_invitados(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    """
    Ver usuarios invitados por mí.
    """
    user_payload = get_current_user(authorization)
    if not user_payload:
        raise HTTPException(status_code=401, detail="Token requerido")
    
    user = db.query(User).filter(User.id == user_payload.get("sub")).first()
    if not user or not user.ruc:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o sin RUC")
    
    invitados = db.query(Invitation).filter(
        Invitation.invitador_ruc == user.ruc
    ).order_by(Invitation.created_at.desc()).all()
    
    result = []
    for inv in invitados:
        registrado = None
        if inv.usada_por:
            registrado_user = db.query(User).filter(User.id == inv.usada_por).first()
            if registrado_user:
                registrado = {
                    "ruc": registrado_user.ruc,
                    "company_name": registrado_user.company_name,
                    "fecha": registrado_user.created_at.isoformat() if registrado_user.created_at else None
                }
        
        result.append({
            "id": inv.id,
            "email": inv.email,
            "ruc_invitado": inv.ruc_invitado,
            "usada": inv.usada,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "expira": inv.expira.isoformat() if inv.expira else None,
            "registrado": registrado
        })
    
    return {
        "success": True,
        "invitados": result,
        "count": len(result),
        "count_registrados": sum(1 for i in invitados if i.usada)
    }
