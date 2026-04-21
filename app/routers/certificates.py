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
    
    if not verification:
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
