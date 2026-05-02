"""
Certificates Router - Conflict Zero
Generación y validación de certificados de verificación.
Cada certificado tiene un código único para validación pública.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import secrets
import os

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_user
from app.models import User, Certificate, VerificationRequest

router = APIRouter(prefix="/certificates", tags=["Certificados"])

ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')


# ============ PYDANTIC MODELS ============

class GenerateCertificateRequest(BaseModel):
    ruc: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    company_name: Optional[str] = None
    score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern=r"^(low|medium|high|critical)$")
    sunat_status: Optional[str] = None
    osce_sanctions_count: Optional[int] = 0
    tce_sanctions_count: Optional[int] = 0
    verification_data: Optional[Dict[str, Any]] = None


class CertificateResponse(BaseModel):
    id: str
    code: str
    ruc: str
    company_name: Optional[str] = None
    score: int
    risk_level: str
    status: str
    generated_at: str
    expires_at: Optional[str] = None
    pdf_url: Optional[str] = None

    class Config:
        orm_mode = True


# ============ HELPERS ============

def _generate_certificate_code() -> str:
    """Genera un código único de certificado (8 caracteres alfanuméricos)."""
    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    return ''.join(secrets.choice(alphabet) for _ in range(8))


def _require_admin(authorization: Optional[str]) -> bool:
    """Valida token de admin."""
    if not authorization or not authorization.startswith('Bearer '):
        return False
    token = authorization.replace('Bearer ', '')
    return token == ADMIN_TOKEN


# ============ ENDPOINTS ============

@router.post("/generate", response_model=CertificateResponse)
async def generate_certificate(
    request: GenerateCertificateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Genera un nuevo certificado de verificación para un RUC.
    El certificado es válido por 90 días.
    """
    # Generar código único
    code = _generate_certificate_code()
    while db.query(Certificate).filter(Certificate.code == code).first():
        code = _generate_certificate_code()
    
    # Crear certificado
    certificate = Certificate(
        id=str(uuid.uuid4()),
        code=code,
        ruc=request.ruc,
        company_name=request.company_name,
        score=request.score,
        risk_level=request.risk_level,
        sunat_status=request.sunat_status,
        osce_sanctions_count=request.osce_sanctions_count or 0,
        tce_sanctions_count=request.tce_sanctions_count or 0,
        generated_by=current_user.id,
        generated_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(days=90),
        status="active",
        verification_data=request.verification_data or {}
    )
    
    db.add(certificate)
    db.commit()
    db.refresh(certificate)
    
    return certificate


@router.get("/verify/{code}")
async def verify_certificate_public(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Verificación pública de certificado.
    Endpoint público - no requiere autenticación.
    Usado desde la página de verificación pública.
    """
    certificate = db.query(Certificate).filter(Certificate.code == code).first()
    
    if not certificate:
        return {
            "success": False,
            "valid": False,
            "message": "Certificado no encontrado"
        }
    
    # Verificar expiración
    is_expired = certificate.expires_at and certificate.expires_at < datetime.utcnow()
    
    if is_expired:
        certificate.status = "expired"
        db.commit()
    
    is_valid = certificate.status == "active" and not is_expired
    
    return {
        "success": True,
        "valid": is_valid,
        "certificate": {
            "code": certificate.code,
            "ruc": certificate.ruc,
            "company_name": certificate.company_name,
            "score": certificate.score,
            "risk_level": certificate.risk_level,
            "status": certificate.status,
            "generated_at": certificate.generated_at.isoformat() if certificate.generated_at else None,
            "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None,
        },
        "message": "Certificado válido" if is_valid else f"Certificado {certificate.status}"
    }


@router.get("/admin/all", response_model=List[CertificateResponse])
async def list_all_certificates(
    authorization: str = Header(None),
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Lista TODOS los certificados (solo admin).
    Requiere ADMIN_TOKEN.
    """
    if not _require_admin(authorization):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requiere token de administrador"
        )
    
    query = db.query(Certificate)
    if status_filter:
        query = query.filter(Certificate.status == status_filter)
    
    return query.order_by(Certificate.generated_at.desc()).all()


@router.get("/{code}")
async def get_certificate(
    code: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene un certificado por su código.
    Endpoint público - usado para validación de certificados.
    """
    certificate = db.query(Certificate).filter(Certificate.code == code).first()
    
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado"
        )
    
    # Verificar si expiró
    if certificate.expires_at and certificate.expires_at < datetime.utcnow():
        certificate.status = "expired"
        db.commit()
    
    if certificate.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Certificado {certificate.status}"
        )
    
    return {
        "success": True,
        "certificate": {
            "code": certificate.code,
            "ruc": certificate.ruc,
            "company_name": certificate.company_name,
            "score": certificate.score,
            "risk_level": certificate.risk_level,
            "sunat_status": certificate.sunat_status,
            "osce_sanctions_count": certificate.osce_sanctions_count,
            "tce_sanctions_count": certificate.tce_sanctions_count,
            "generated_at": certificate.generated_at.isoformat() if certificate.generated_at else None,
            "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None,
            "status": certificate.status,
            "verification_data": certificate.verification_data
        }
    }


@router.get("/", response_model=List[CertificateResponse])
async def list_certificates(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Lista los certificados generados por el usuario.
    Admins pueden ver todos los certificados.
    """
    query = db.query(Certificate)
    
    if not current_user.is_admin:
        query = query.filter(Certificate.generated_by == current_user.id)
    
    certificates = query.order_by(Certificate.generated_at.desc()).all()
    return certificates


@router.post("/{certificate_id}/revoke")
async def revoke_certificate(
    certificate_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Revoca un certificado activo.
    Solo el generador o un admin puede revocar.
    """
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    
    if not certificate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Certificado no encontrado"
        )
    
    if certificate.generated_by != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para revocar este certificado"
        )
    
    if certificate.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El certificado ya está {certificate.status}"
        )
    
    certificate.status = "revoked"
    db.commit()
    
    return {
        "success": True,
        "message": "Certificado revocado exitosamente"
    }
