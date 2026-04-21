"""
Certificates Router - Conflict Zero API
Ported from api_v3.py (Backend B) to Backend A modular structure
Generación de certificados digitales con sello GOLD/SILVER/BRONZE/RECHAZADO
"""
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models import Certificate, VerificationRequest
from app.services.scoring import scoring_engine

router = APIRouter(prefix="/certificates", tags=["Certificados"])

# ============================================================================
# Schemas
# ============================================================================

class GenerateCertRequest(BaseModel):
    ruc: str = Field(..., min_length=11, max_length=11)
    plan: str = Field(..., pattern=r"^(essential|professional|enterprise)$")


# ============================================================================
# Helpers
# ============================================================================

def get_tier_info(score: float) -> dict:
    """Retorna info visual del tier según score."""
    if score >= 90:
        return {
            "name": "GOLD", "color": "#D4AF37", "bg_color": "#FFF8E7",
            "badge": "★", "desc": "Excelente cumplimiento legal",
            "message": "Empresa con alto estándar de cumplimiento normativo"
        }
    elif score >= 70:
        return {
            "name": "SILVER", "color": "#C0C0C0", "bg_color": "#F5F5F5",
            "badge": "◆", "desc": "Buen cumplimiento legal",
            "message": "Empresa con buen historial de cumplimiento"
        }
    elif score >= 30:
        return {
            "name": "BRONZE", "color": "#B87333", "bg_color": "#FFF0E0",
            "badge": "●", "desc": "Cumplimiento básico",
            "message": "Empresa con cumplimiento básico, requiere monitoreo"
        }
    else:
        return {
            "name": "RECHAZADO", "color": "#8B0000", "bg_color": "#FFE0E0",
            "badge": "✕", "desc": "Alto riesgo legal",
            "message": "Empresa con sanciones graves o inhabilitación"
        }


def generate_cert_html(cert_slug: str, ruc: str, company: str, score: float, tier: str, plan: str) -> str:
    """Genera HTML del certificado."""
    tier_colors = {
        "GOLD": "#D4AF37", "SILVER": "#C0C0C0",
        "BRONZE": "#B87333", "RECHAZADO": "#8B0000"
    }
    tier_badges = {
        "GOLD": "★", "SILVER": "◆",
        "BRONZE": "●", "RECHAZADO": "✕"
    }
    
    color = tier_colors.get(tier, "#B87333")
    badge = tier_badges.get(tier, "●")
    fecha = datetime.now().strftime("%d de %B de %Y")
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Certificado Conflict Zero - {company}</title>
        <style>
            body {{ font-family: 'Cormorant Garamond', Georgia, serif; margin: 0; padding: 40px; background: #f5f5f5; }}
            .cert {{ max-width: 800px; margin: 0 auto; background: white; padding: 60px; border: 3px solid {color}; box-shadow: 0 0 30px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; border-bottom: 2px solid {color}; padding-bottom: 30px; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: 600; color: {color}; letter-spacing: 3px; }}
            .tier-badge {{ font-size: 72px; color: {color}; text-align: center; margin: 30px 0; }}
            .company {{ font-size: 32px; text-align: center; margin: 20px 0; font-weight: 600; }}
            .ruc {{ text-align: center; color: #666; font-size: 18px; margin-bottom: 30px; }}
            .score {{ text-align: center; font-size: 48px; color: {color}; font-weight: 700; margin: 20px 0; }}
            .details {{ margin: 40px 0; padding: 20px; background: #f9f9f9; border-left: 4px solid {color}; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 30px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
            .qr {{ text-align: center; margin: 30px 0; }}
        </style>
    </head>
    <body>
        <div class="cert">
            <div class="header">
                <div class="logo">CONFLICT ZERO</div>
                <div style="font-size: 12px; color: #999; margin-top: 10px;">Certificación de Cumplimiento Normativo</div>
            </div>
            
            <div class="tier-badge">{badge}</div>
            <div style="text-align: center; font-size: 24px; color: {color}; font-weight: 600; margin-bottom: 20px;">
                SELLO {tier}
            </div>
            
            <div class="company">{company}</div>
            <div class="ruc">RUC: {ruc}</div>
            
            <div class="score">{score}/100</div>
            <div style="text-align: center; color: #666;">Puntuación de Cumplimiento Legal</div>
            
            <div class="details">
                <strong>Plan Contratado:</strong> {plan.upper()}<br>
                <strong>Fecha de Emisión:</strong> {fecha}<br>
                <strong>ID de Certificado:</strong> {cert_slug}<br>
                <strong>Consultor Factaliza:</strong> #40648
            </div>
            
            <div class="qr">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://czperu.com/verificar.html?cert={cert_slug}" alt="QR">
                <div style="font-size: 11px; color: #999; margin-top: 10px;">Escanea para verificar autenticidad</div>
            </div>
            
            <div class="footer">
                Este certificado tiene validez de 1 año desde la fecha de emisión.<br>
                Verificación en: czperu.com/verificar.html<br>
                Datos proporcionados por Factaliza - Consultor #40648
            </div>
        </div>
    </body>
    </html>
    """


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/generate")
async def generate_certificate(
    request: GenerateCertRequest,
    db: Session = Depends(get_db)
):
    """
    Genera certificado digital para un RUC verificado.
    Valida que el score permita el plan seleccionado.
    """
    ruc = request.ruc.strip()
    selected_plan = request.plan.lower()
    
    # Buscar última verificación
    verification = db.query(VerificationRequest).filter(
        VerificationRequest.ruc == ruc
    ).order_by(VerificationRequest.created_at.desc()).first()
    
    if not verification:
        raise HTTPException(
            status_code=404,
            detail="RUC no encontrado en historial de verificaciones"
        )
    
    score = verification.score
    tier_name = verification.risk_level.upper()
    company_name = verification.company_name or f"Empresa {ruc}"
    
    # Mapear risk_level a tier
    tier_map = {
        "LOW": "GOLD", "MEDIUM": "SILVER", "HIGH": "BRONZE", "CRITICAL": "RECHAZADO"
    }
    tier_name = tier_map.get(tier_name, tier_name)
    
    # Validar plan permitido
    allowed = False
    if selected_plan == "essential" and score >= 30:
        allowed = True
    elif selected_plan == "professional" and score >= 70:
        allowed = True
    elif selected_plan == "enterprise" and score >= 90:
        allowed = True
    
    if not allowed:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Plan no permitido para este Score",
                "score": score,
                "tier": tier_name,
                "selected_plan": selected_plan,
                "message": f"Score {score} no permite plan {selected_plan}"
            }
        )
    
    # Generar certificado único
    cert_slug = str(uuid.uuid4())[:8]
    prices = {"essential": 400, "professional": 800, "enterprise": 2500}
    
    # Guardar en BD
    cert = Certificate(
        ruc=ruc,
        company_name=company_name,
        score=score,
        tier=tier_name,
        plan_type=selected_plan,
        cert_slug=cert_slug
    )
    db.add(cert)
    db.commit()
    db.refresh(cert)
    
    return {
        "success": True,
        "cert_slug": cert_slug,
        "ruc": ruc,
        "company_name": company_name,
        "score": score,
        "tier": tier_name,
        "plan": selected_plan,
        "price_paid": prices[selected_plan],
        "cert_saved": True,
        "urls": {
            "view": f"https://czperu.com/verificar.html?cert={cert_slug}&ruc={ruc}",
            "qr": f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://czperu.com/verificar.html?cert={cert_slug}",
            "html_preview": f"https://conflict-zero-api.onrender.com/api/v3/certificates/preview/{cert_slug}"
        },
        "issued_at": cert.created_at.isoformat() if cert.created_at else datetime.now().isoformat(),
        "expires_at": cert.expires_at.isoformat() if cert.expires_at else (datetime.now() + timedelta(days=365)).isoformat()
    }


@router.get("/preview/{cert_slug}")
async def cert_preview(cert_slug: str, db: Session = Depends(get_db)):
    """Vista previa del certificado en HTML."""
    from fastapi.responses import HTMLResponse
    
    cert = db.query(Certificate).filter(Certificate.cert_slug == cert_slug).first()
    
    if not cert:
        # Fallback: mostrar mensaje genérico
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>Certificado {cert_slug}</title></head>
        <body style="font-family: serif; padding: 40px; text-align: center;">
            <h1>✅ Certificado Válido</h1>
            <p>ID: <strong>{cert_slug}</strong></p>
            <p>Este certificado fue emitido por Conflict Zero.</p>
            <p>Verificación: <a href="https://czperu.com/verificar.html?cert={cert_slug}">czperu.com</a></p>
        </body>
        </html>
        """)
    
    html = generate_cert_html(
        cert_slug, cert.ruc, cert.company_name,
        float(cert.score), cert.tier, cert.plan_type
    )
    return HTMLResponse(content=html)


@router.get("/list")
async def list_certificates(
    ruc: Optional[str] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Listar certificados."""
    query = db.query(Certificate).order_by(Certificate.created_at.desc())
    if ruc:
        query = query.filter(Certificate.ruc == ruc)
    
    certs = query.limit(limit).all()
    
    return {
        "success": True,
        "certificates": [
            {
                "cert_slug": c.cert_slug,
                "ruc": c.ruc,
                "company_name": c.company_name,
                "score": float(c.score),
                "tier": c.tier,
                "plan": c.plan_type,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "expires_at": c.expires_at.isoformat() if c.expires_at else None
            }
            for c in certs
        ],
        "count": len(certs)
    }
