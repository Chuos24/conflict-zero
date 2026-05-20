"""
PDF Certificate Service - Conflict Zero
Genera certificados PDF premium con QR code de verificación.
"""

import io
import qrcode
import qrcode.image.pil
from datetime import datetime
from typing import Optional, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ── Paleta ConflictZero ───────────────────────────────────────
COLOR_FONDO    = HexColor("#0A0A0F")
COLOR_ORO      = HexColor("#C5A059")
COLOR_PLATA    = HexColor("#C0C0C0")
COLOR_TEXTO    = HexColor("#F5F5F0")
COLOR_GRIS     = HexColor("#1A1A24")
COLOR_BORDE    = HexColor("#2A2A3A")

RISK_COLORS = {
    "low":      HexColor("#22C55E"),
    "medium":   HexColor("#F59E0B"),
    "high":     HexColor("#EF4444"),
    "critical": HexColor("#7C3AED"),
}

RISK_LABELS = {
    "low":      "RIESGO BAJO",
    "medium":   "RIESGO MODERADO",
    "high":     "RIESGO ALTO",
    "critical": "RIESGO CRÍTICO",
}


def _generate_qr(url: str, size: int = 200) -> io.BytesIO:
    """Genera QR code como imagen en memoria."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=6,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#C5A059", back_color="#0A0A0F")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def _draw_rounded_rect(c: canvas.Canvas, x, y, w, h, r, fill_color=None, stroke_color=None, stroke_width=1):
    """Dibuja rectángulo con esquinas redondeadas."""
    if fill_color:
        c.setFillColor(fill_color)
    if stroke_color:
        c.setStrokeColor(stroke_color)
        c.setLineWidth(stroke_width)
    else:
        c.setLineWidth(0)
    c.roundRect(x, y, w, h, r, fill=1 if fill_color else 0, stroke=1 if stroke_color else 0)


def generate_certificate_pdf(
    code: str,
    ruc: str,
    company_name: str,
    score: int,
    risk_level: str,
    generated_at: datetime,
    expires_at: Optional[datetime],
    sunat_status: Optional[str] = None,
    osce_sanctions_count: int = 0,
    tce_sanctions_count: int = 0,
    verification_url: Optional[str] = None,
) -> bytes:
    """
    Genera un PDF de certificado premium estilo ConflictZero.
    Retorna los bytes del PDF.
    """
    buf = io.BytesIO()
    W, H = A4  # 595 x 842 pts

    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Certificado ConflictZero - {ruc}")

    # ── FONDO COMPLETO ──────────────────────────────────────────
    c.setFillColor(COLOR_FONDO)
    c.rect(0, 0, W, H, fill=1, stroke=0)

    # ── BORDE DORADO ────────────────────────────────────────────
    c.setStrokeColor(COLOR_ORO)
    c.setLineWidth(1.5)
    c.roundRect(12, 12, W - 24, H - 24, 8, fill=0, stroke=1)

    # ── HEADER BAND ─────────────────────────────────────────────
    header_h = 90
    _draw_rounded_rect(c, 20, H - 20 - header_h, W - 40, header_h, 6,
                       fill_color=COLOR_GRIS, stroke_color=COLOR_ORO, stroke_width=0.5)

    # Logo / Brand
    c.setFillColor(COLOR_ORO)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(36, H - 58, "CONFLICT")
    c.setFillColor(COLOR_PLATA)
    c.drawString(36 + c.stringWidth("CONFLICT", "Helvetica-Bold", 22), H - 58, "ZERO")

    c.setFillColor(COLOR_PLATA)
    c.setFont("Helvetica", 8)
    c.drawString(36, H - 72, "PLATAFORMA DE VERIFICACIÓN EMPRESARIAL")

    # Código del certificado (top right)
    c.setFillColor(COLOR_ORO)
    c.setFont("Helvetica-Bold", 10)
    code_label = f"CERT # {code.upper()}"
    c.drawRightString(W - 36, H - 52, code_label)
    c.setFillColor(COLOR_PLATA)
    c.setFont("Helvetica", 8)
    c.drawRightString(W - 36, H - 66, "conflictzero.com/verify")

    # ── TÍTULO CERTIFICADO ──────────────────────────────────────
    y = H - 140
    c.setFillColor(COLOR_ORO)
    c.setFont("Helvetica-Bold", 13)
    c.drawCentredString(W / 2, y, "CERTIFICADO DE VERIFICACIÓN DE RIESGO")

    # ── EMPRESA ─────────────────────────────────────────────────
    y -= 28
    c.setFillColor(COLOR_TEXTO)
    c.setFont("Helvetica-Bold", 18)
    name = (company_name or "Empresa Desconocida")[:50]
    c.drawCentredString(W / 2, y, name)

    y -= 16
    c.setFillColor(COLOR_PLATA)
    c.setFont("Helvetica", 11)
    c.drawCentredString(W / 2, y, f"RUC {ruc}")

    # ── SEPARADOR ───────────────────────────────────────────────
    y -= 20
    c.setStrokeColor(COLOR_ORO)
    c.setLineWidth(0.5)
    c.line(40, y, W - 40, y)

    # ── SCORE PRINCIPAL ─────────────────────────────────────────
    y -= 16
    risk_color = RISK_COLORS.get(risk_level, COLOR_PLATA)
    risk_label = RISK_LABELS.get(risk_level, risk_level.upper())

    # Score circle (simulado con rectángulo redondeado)
    circle_x = W / 2 - 45
    circle_y = y - 80
    _draw_rounded_rect(c, circle_x, circle_y, 90, 85, 45,
                       fill_color=COLOR_GRIS, stroke_color=risk_color, stroke_width=2)

    c.setFillColor(risk_color)
    c.setFont("Helvetica-Bold", 38)
    score_str = str(score)
    c.drawCentredString(W / 2, circle_y + 44, score_str)

    c.setFillColor(COLOR_PLATA)
    c.setFont("Helvetica", 9)
    c.drawCentredString(W / 2, circle_y + 28, "/ 100")

    # Risk badge
    badge_w = 140
    badge_x = W / 2 - badge_w / 2
    badge_y = circle_y - 28
    _draw_rounded_rect(c, badge_x, badge_y, badge_w, 22, 4, fill_color=risk_color)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(W / 2, badge_y + 7, risk_label)

    # ── DATOS DETALLE ────────────────────────────────────────────
    y = badge_y - 28
    c.setStrokeColor(COLOR_BORDE)
    c.setLineWidth(0.5)
    c.line(40, y, W - 40, y)

    y -= 16
    col1_x = 50
    col2_x = W / 2 + 10

    def draw_field(x, yy, label, value, value_color=None):
        c.setFillColor(COLOR_PLATA)
        c.setFont("Helvetica", 8)
        c.drawString(x, yy + 12, label.upper())
        c.setFillColor(value_color or COLOR_TEXTO)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, yy, str(value))

    sunat_val = (sunat_status or "ACTIVO").upper()
    sunat_color = HexColor("#22C55E") if "ACTIVO" in sunat_val else HexColor("#EF4444")

    draw_field(col1_x, y, "Estado SUNAT", sunat_val, sunat_color)
    draw_field(col2_x, y, "Sanciones OSCE",
               f"{osce_sanctions_count} sanción(es)" if osce_sanctions_count else "Sin sanciones",
               HexColor("#EF4444") if osce_sanctions_count else HexColor("#22C55E"))

    y -= 44
    draw_field(col1_x, y, "Sanciones TCE / RNP",
               f"{tce_sanctions_count} sanción(es)" if tce_sanctions_count else "Sin sanciones",
               HexColor("#EF4444") if tce_sanctions_count else HexColor("#22C55E"))
    draw_field(col2_x, y, "Fecha de emisión",
               generated_at.strftime("%d/%m/%Y"))

    y -= 44
    draw_field(col1_x, y, "Válido hasta",
               expires_at.strftime("%d/%m/%Y") if expires_at else "90 días")
    draw_field(col2_x, y, "Código de verificación",
               code.upper(), COLOR_ORO)

    # ── SEPARADOR ───────────────────────────────────────────────
    y -= 24
    c.setStrokeColor(COLOR_BORDE)
    c.setLineWidth(0.5)
    c.line(40, y, W - 40, y)

    # ── QR CODE ─────────────────────────────────────────────────
    verify_url = verification_url or f"https://conflict-zero-api.onrender.com/api/v3/certificates/verify/{code}"
    qr_buf = _generate_qr(verify_url)

    qr_size = 90
    qr_x = W / 2 - qr_size / 2
    qr_y = y - qr_size - 14

    # Marco QR
    _draw_rounded_rect(c, qr_x - 8, qr_y - 8, qr_size + 16, qr_size + 16, 4,
                       fill_color=COLOR_GRIS, stroke_color=COLOR_ORO, stroke_width=0.5)

    c.drawImage(qr_buf, qr_x, qr_y, width=qr_size, height=qr_size, mask="auto")

    c.setFillColor(COLOR_PLATA)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, qr_y - 14, "Escanea para verificar autenticidad")

    # ── FOOTER ──────────────────────────────────────────────────
    footer_y = 28
    c.setFillColor(COLOR_PLATA)
    c.setFont("Helvetica", 7)
    c.drawCentredString(W / 2, footer_y + 10,
        "Este certificado fue generado automáticamente por ConflictZero · conflictzero.com")
    c.drawCentredString(W / 2, footer_y,
        f"Verificación: {verify_url}")

    c.setStrokeColor(COLOR_ORO)
    c.setLineWidth(0.3)
    c.line(40, footer_y + 22, W - 40, footer_y + 22)

    c.save()
    return buf.getvalue()
