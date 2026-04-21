"""
Certificates Router - Endpoint para verificación de certificados por slug
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta

router = APIRouter(prefix="/certificates", tags=["Certificados"])

# Certificados de demo — mapean a los HTML estáticos existentes
CERTIFICATES_DEMO = {
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


def _is_expired(cert: dict) -> bool:
    expires = cert.get("expires_at")
    if not expires:
        return False
    try:
        return datetime.fromisoformat(expires.replace("Z", "+00:00")) < datetime.utcnow()
    except:
        return False


@router.get("/{slug}")
async def get_certificate(slug: str):
    """
    Verifica un certificado por su código slug.
    Si es un RUC de 11 dígitos, devuelve certificado generado dinámicamente.
    """
    # Si es un RUC de 11 dígitos, generar certificado dinámico
    if slug.isdigit() and len(slug) == 11:
        # Certificado genérico para cualquier RUC consultado por este endpoint
        cert = {
            "slug": slug,
            "tier": "GOLD",
            "score": 96,
            "company_name": f"Empresa RUC {slug}",
            "ruc": slug,
            "plan": "Enterprise",
            "issued_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(days=365)).isoformat(),
        }
        return {
            "success": True,
            "certificate": cert,
            "valid": True,
        }

    # Buscar en certificados demo
    cert = CERTIFICATES_DEMO.get(slug)
    if not cert:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")

    is_expired = _is_expired(cert)

    return {
        "success": True,
        "certificate": cert,
        "valid": not is_expired,
        "expired": is_expired,
    }
