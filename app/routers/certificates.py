from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models import VerificationRequest

router = APIRouter(prefix="/certificates", tags=["Certificados"])

# Mapeo de risk_level a tier
RISK_TO_TIER = {
    "LOW": "GOLD",
    "MEDIUM": "SILVER",
    "HIGH": "BRONZE",
    "CRITICAL": "RECHAZADO"
}

@router.get("/{slug}")
async def get_certificate(slug: str, db: Session = Depends(get_db)):
    """
    Obtiene un certificado por su slug.
    El slug puede ser:
    - Los primeros 8 caracteres del UUID de la verificación
    - El UUID completo
    """
    # Buscar por UUID completo o por prefijo de 8 caracteres
    verification = None
    
    # Primero intentar match exacto de UUID
    if len(slug) == 36:
        verification = db.query(VerificationRequest).filter(
            VerificationRequest.id == slug
        ).first()
    
    # Si no, buscar por prefijo de 8 caracteres
    if not verification and len(slug) >= 8:
        # Para SQLite (LIKE es case-insensitive por defecto)
        verification = db.query(VerificationRequest).filter(
            VerificationRequest.id.like(f"{slug}%")
        ).first()
    
    # Fallback: certificados demo para slugs conocidos
    DEMO_CERTIFICATES = {
        "a3f9k2m8": {
            "slug": "a3f9k2m8",
            "tier": "GOLD",
            "score": 96,
            "company_name": "Constructora Líder del Perú SAC",
            "ruc": "20100123091",
            "plan": "Enterprise",
            "issued_at": "2026-01-15T00:00:00",
            "expires_at": "2027-01-15T00:00:00",
        },
        "b7k2m9p4": {
            "slug": "b7k2m9p4",
            "tier": "SILVER",
            "score": 82,
            "company_name": "Ingeniería Construcciones SAC",
            "ruc": "20100123092",
            "plan": "Professional",
            "issued_at": "2026-02-01T00:00:00",
            "expires_at": "2027-02-01T00:00:00",
        },
        "c9x4n1q7": {
            "slug": "c9x4n1q7",
            "tier": "BRONZE",
            "score": 65,
            "company_name": "Servicios Constructores EIRL",
            "ruc": "20100123093",
            "plan": "Starter",
            "issued_at": "2026-03-10T00:00:00",
            "expires_at": "2027-03-10T00:00:00",
        },
        "demo-expired": {
            "slug": "demo-expired",
            "tier": "RECHAZADO",
            "score": 15,
            "company_name": "Constructora Problemática SAC",
            "ruc": "20999999001",
            "plan": "N/A",
            "issued_at": "2025-01-01T00:00:00",
            "expires_at": "2026-01-01T00:00:00",
        },
    }
    
    if not verification:
        # Intentar certificado demo
        demo = DEMO_CERTIFICATES.get(slug)
        if demo:
            is_expired = datetime.fromisoformat(demo["expires_at"].replace("Z", "+00:00")) < datetime.utcnow() if demo.get("expires_at") else False
            return {
                "success": True,
                "valid": not is_expired,
                "expired": is_expired,
                "certificate": demo,
            }
        
        raise HTTPException(
            status_code=404,
            detail={"error": "CERTIFICATE_NOT_FOUND", "message": "Certificado no encontrado"}
        )
    
    # Calcular vigencia (1 año desde la emisión)
    issued_at = verification.created_at or datetime.utcnow()
    expires_at = issued_at + timedelta(days=365)
    is_valid = datetime.utcnow() < expires_at
    
    # Construir respuesta
    tier = RISK_TO_TIER.get(verification.risk_level.upper(), "BRONZE")
    
    # El slug del certificado son los primeros 8 caracteres del UUID
    cert_slug = verification.id[:8]
    
    return {
        "success": True,
        "valid": is_valid,
        "certificate": {
            "slug": cert_slug,
            "tier": tier,
            "score": verification.score,
            "company_name": verification.company_name or "Empresa sin nombre",
            "ruc": verification.ruc,
            "plan": "Professional",  # Default, podríamos obtener del usuario
            "issued_at": issued_at.isoformat(),
            "expires_at": expires_at.isoformat()
        }
    }
