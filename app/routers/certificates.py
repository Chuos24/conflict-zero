"""
Certificates Router - Conflict Zero
Generación y validación de certificados de verificación.
Cada certificado tiene un código único para validación pública.
Incluye generación de PDF con QR code embebido.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import secrets
import os
import io

# PDF + QR
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm, mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image

from app.core.database import get_db
from app.core.security import get_current_active_user, get_current_user
from app.models import User, Certificate, VerificationRequest

router = APIRouter(prefix="/certificates", tags=["Certificados"])

ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')
BASE_URL = os.environ.get('BASE_URL', 'https://czperu.com')


# ============ PYDANTIC MODELS ============

class GenerateCertificateRequest(BaseModel):
    ruc: str = Field(..., min_length=11, max_length=11, pattern=r'^\d{11}$')
    company_name: Optional[str] = None
    score: int = Field(..., ge=0, le=100)
    risk_level: str = Field(..., pattern=r'^(low|medium|high|critical)$')
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

    model_config = ConfigDict(from_attributes=True)


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


def _get_risk_color(risk_level: str):
    """Retorna color HEX según nivel de riesgo."""
    return {
        "low": colors.HexColor("#22c55e"),
        "medium": colors.HexColor("#f59e0b"),
        "high": colors.HexColor("#ef4444"),
        "critical": colors.HexColor("#7f1d1d"),
    }.get(risk_level, colors.HexColor("#6b7280"))


def _get_risk_label(risk_level: str) -> str:
    return {
        "low": "RIESGO BAJO",
        "medium": "RIESGO MODERADO",
        "high": "RIESGO ALTO",
        "critical": "RIESFO CRÍTICO",
    }.get(risk_level, "DESCONOCIDO")


def _generate_qr_image(data: str) -> Image.Image:
    """Genera imagen QR como PIL Image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#C5A059", back_color="white").convert("RGB")


def _generate_pdf_bytes(certificate) -> bytes:
    """
    Genera el PDF del certificado con diseño premium ConflictZero.
    Retorna bytes del PDF listo para descargar.
    """
    buffer = io.BytesIO()
    page_width, page_height = A4

    c = canvas.Canvas(buffer, pagesize=A4)

    # Fondo oscuro premium
    c.setFillColor(colors.HexColor("#0A0A0F"))
    c.rect(0, 0, page_width, page_height, fill=1, stroke=0)

    # Banda dorada superior
    c.setFillColor(colors.HexColor("#C5A059"))
    c.rect(0, page_height - 8*mm, page_width, 8*mm, fill=1, stroke=0)

    # Banda dorada inferior
    c.rect(0, 0, page_width, 8*mm, fill=1, stroke=0)

    # Línea decorativa dorada
    c.setStrokeColor(colors.HexColor("#C5A059"))
    c.setLineWidth(0.5)
    c.line(20*mm, page_height - 18*mm, page_width - 20*mm, page_height - 18*mm)
    c.line(20*mm, 18*mm, page_width - 20*mm, 18*mm)

    # Logo / Nombre del producto
    c.setFillColor(colors.HexColor("#C5A059"))
    c.setFont("Helvetica-Bold", 22)
    c.drawCentredString(page_width / 2, page_height - 30*mm, "CONFLICT ZERO")

    c.setFillColor(colors.HexColor("#C0C0C0"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(page_width / 2, page_height - 36*mm, "SISTEMA DE VERIFICACIÓN DE INTEGRIDAD EMPRESARIAL")

    # Título del documento
    c.setFillColor(colors.HexColor("#F5F5F0"))
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(page_width / 2, page_height - 50*mm, "CERTIFICADO DE VERIFICACIÓN")

    c.setFillColor(colors.HexColor("#C0C0C0"))
    c.setFont("Helvetica", 10)
    c.drawCentredString(page_width / 2, page_height - 56*mm, f"Código: {certificate.code.upper()}")

    # Score prominente
    risk_color = _get_risk_color(certificate.risk_level)
    score_x = page_width / 2
    score_y = page_height - 88*mm

    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.circle(score_x, score_y, 25*mm, fill=1, stroke=0)
    c.setStrokeColor(risk_color)
    c.setLineWidth(2)
    c.circle(score_x, score_y, 25*mm, fill=0, stroke=1)

    c.setFillColor(risk_color)
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(score_x, score_y + 4*mm, str(certificate.score))
    c.setFont("Helvetica", 9)
    c.drawCentredString(score_x, score_y - 8*mm, "SCORE")

    # Badge de riesgo
    label = _get_risk_label(certificate.risk_level)
    badge_w = 50*mm
    badge_h = 8*mm
    badge_x = score_x - badge_w / 2
    badge_y = score_y - 36*mm
    c.setFillColor(risk_color)
    c.roundRect(badge_x, badge_y, badge_w, badge_h, 2*mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(score_x, badge_y + 2.5*mm, label)

    # Datos de la empresa
    data_y = page_height - 145*mm
    c.setFillColor(colors.HexColor("#1a1a2e"))
    c.roundRect(20*mm, data_y - 40*mm, page_width - 40*mm, 42*mm, 3*mm, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#C5A059"))
    c.setLineWidth(0.5)
    c.roundRect(20*mm, data_y - 40*mm, page_width - 40*mm, 42*mm, 3*mm, fill=0, stroke=1)

    c.setFillColor(colors.HexColor("#C5A059"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(25*mm, data_y - 6*mm, "RAZÓN SOCIAL")
    c.setFillColor(colors.HexColor("#F5F5F0"))
    c.setFont("Helvetica-Bold", 12)
    company = (certificate.company_name or "No disponible")[:45]
    c.drawString(25*mm, data_y - 13*mm, company)

    c.setFillColor(colors.HexColor("#C5A059"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(25*mm, data_y - 21*mm, "RUC")
    c.setFillColor(colors.HexColor("#F5F5F0"))
    c.setFont("Helvetica", 11)
    c.drawString(25*mm, data_y - 27*mm, certificate.ruc)

    if certificate.sunat_status:
        c.setFillColor(colors.HexColor("#C5A059"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(90*mm, data_y - 21*mm, "ESTADO SUNAT")
        c.setFillColor(colors.HexColor("#F5F5F0"))
        c.setFont("Helvetica", 11)
        c.drawString(90*mm, data_y - 27*mm, certificate.sunat_status)

    c.setFillColor(colors.HexColor("#C5A059"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(25*mm, data_y - 35*mm, "SANCIONES OSCE")
    c.setFillColor(colors.HexColor("#F5F5F0"))
    c.setFont("Helvetica", 11)
    c.drawString(25*mm, data_y - 41*mm, str(certificate.osce_sanctions_count or 0))

    c.setFillColor(colors.HexColor("#C5A059"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(90*mm, data_y - 35*mm, "SANCIONES TCE")
    c.setFillColor(colors.HexColor("#F5F5F0"))
    c.setFont("Helvetica", 11)
    c.drawString(90*mm, data_y - 41*mm, str(certificate.tce_sanctions_count or 0))

    # QR Code
    verify_url = f"{BASE_URL}/verify/{certificate.code}"
    qr_img = _generate_qr_image(verify_url)
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_reader = ImageReader(qr_buffer)

    qr_size = 35*mm
    qr_x = page_width - 20*mm - qr_size
    qr_y = 35*mm
    c.setFillColor(colors.white)
    c.roundRect(qr_x - 3*mm, qr_y - 3*mm, qr_size + 6*mm, qr_size + 6*mm, 2*mm, fill=1, stroke=0)
    c.drawImage(qr_reader, qr_x, qr_y, width=qr_size, height=qr_size)

    c.setFillColor(colors.HexColor("#C0C0C0"))
    c.setFont("Helvetica", 7)
    c.drawCentredString(qr_x + qr_size/2, qr_y - 7*mm, "Escanear para verificar")

    # Fechas y código
    c.setFillColor(colors.HexColor("#C0C0C0"))
    c.setFont("Helvetica", 8)
    gen_date = certificate.generated_at.strftime("%d/%m/%Y") if certificate.generated_at else "—"
    exp_date = certificate.expires_at.strftime("%d/%m/%Y") if certificate.expires_at else "—"
    c.drawString(20*mm, 55*mm, f"Emitido: {gen_date}")
    c.drawString(20*mm, 50*mm, f"Válido hasta: {exp_date}")
    c.drawString(20*mm, 45*mm, f"URL: {verify_url}")

    # Footer
    c.setFillColor(colors.HexColor("#6b7280"))
    c.setFont("Helvetica", 7)
    c.drawCentredString(page_width / 2, 13*mm,
        "Este certificado es generado automáticamente por ConflictZero. Verificar autenticidad en czperu.com")

    c.save()
    buffer.seek(0)
    return buffer.read()


# ============ ENDPOINTS ============

@router.post("/generate", response_model=CertificateResponse)
async def generate_certificate(
    request: GenerateCertificateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    code = _generate_certificate_code()
    while db.query(Certificate).filter(Certificate.code == code).first():
        code = _generate_certificate_code()

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

    return CertificateResponse(
        id=certificate.id,
        code=certificate.code,
        ruc=certificate.ruc,
        company_name=certificate.company_name,
        score=certificate.score,
        risk_level=certificate.risk_level,
        status=certificate.status,
        generated_at=certificate.generated_at.isoformat(),
        expires_at=certificate.expires_at.isoformat() if certificate.expires_at else None,
        pdf_url=f"/api/v3/certificates/{certificate.code}/pdf"
    )


@router.get("/{code}/pdf")
async def download_certificate_pdf(
    code: str,
    db: Session = Depends(get_db)
):
    certificate = db.query(Certificate).filter(Certificate.code == code).first()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    if certificate.expires_at and certificate.expires_at < datetime.utcnow():
        certificate.status = "expired"
        db.commit()
    if certificate.status != "active":
        raise HTTPException(status_code=400, detail=f"Certificado {certificate.status}")
    pdf_bytes = _generate_pdf_bytes(certificate)
    filename = f"certificado-kz-{certificate.ruc}-{certificate.code}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/verify/{code}")
async def verify_certificate_public(code: str, db: Session = Depends(get_db)):
    certificate = db.query(Certificate).filter(Certificate.code == code).first()
    if not certificate:
        return {"success": False, "valid": False, "message": "Certificado no encontrado"}
    is_expired = certificate.expires_at and certificate.expires_at < datetime.utcnow()
    if is_expired:
        certificate.status = "expired"
        db.commit()
    is_valid = certificate.status == "active" and not is_expired
    return {
        "success": True, "valid": is_valid,
        "certificate": {
            "code": certificate.code, "ruc": certificate.ruc,
            "company_name": certificate.company_name, "score": certificate.score,
            "risk_level": certificate.risk_level, "status": certificate.status,
            "generated_at": certificate.generated_at.isoformat() if certificate.generated_at else None,
            "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None,
            "pdf_url": f"/api/v3/certificates/{certificate.code}/pdf"
        },
        "message": "Certificado válido" if is_valid else f"Certificado {certificate.status}"
    }


@router.get("/admin/all", response_model=List[CertificateResponse])
async def list_all_certificates(authorization: str = Header(None), status_filter: Optional[str] = None, db: Session = Depends(get_db)):
    if not _require_admin(authorization):
        raise HTTPException(status_code=403, detail="Se requiere token de administrador")
    query = db.query(Certificate)
    if status_filter:
        query = query.filter(Certificate.status == status_filter)
    return query.order_by(Certificate.generated_at.desc()).all()


@router.get("/{code}")
async def get_certificate(code: str, db: Session = Depends(get_db)):
    certificate = db.query(Certificate).filter(Certificate.code == code).first()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    if certificate.expires_at and certificate.expires_at < datetime.utcnow():
        certificate.status = "expired"
        db.commit()
    if certificate.status != "active":
        raise HTTPException(status_code=400, detail=f"Certificado {certificate.status}")
    return {"success": True, "certificate": {"code": certificate.code, "ruc": certificate.ruc, "company_name": certificate.company_name, "score": certificate.score, "risk_level": certificate.risk_level, "sunat_status": certificate.sunat_status, "osce_sanctions_count": certificate.osce_sanctions_count, "tce_sanctions_count": certificate.tce_sanctions_count, "generated_at": certificate.generated_at.isoformat() if certificate.generated_at else None, "expires_at": certificate.expires_at.isoformat() if certificate.expires_at else None, "status": certificate.status, "verification_data": certificate.verification_data, "pdf_url": f"/api/v3/certificates/{certificate.code}/pdf"}}


@router.get("/", response_model=List[CertificateResponse])
async def list_certificates(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    query = db.query(Certificate)
    if not current_user.is_admin:
        query = query.filter(Certificate.generated_by == current_user.id)
    return query.order_by(Certificate.generated_at.desc()).all()


@router.post("/{certificate_id}/revoke")
async def revoke_certificate(certificate_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    certificate = db.query(Certificate).filter(Certificate.id == certificate_id).first()
    if not certificate:
        raise HTTPException(status_code=404, detail="Certificado no encontrado")
    if certificate.generated_by != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="No tienes permiso para revocar_este_certificado")
    if certificate.status != "active":
        raise HTTPException(status_code=400, detail=f"El certificado ya está {certificate.status}")
    certificate.status = "revoked"
    db.commit()
    return {"success": True, "message": "Certificado revocado exitosamente"}
