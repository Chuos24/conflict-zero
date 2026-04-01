"""
Email Router - Conflict Zero
Endpoints para envío de notificaciones por email
"""
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from app.services.email_service import (
    send_welcome_email,
    send_low_credit_alert,
    send_monthly_report,
    send_admin_notification,
    email_service
)

router = APIRouter(tags=["Notificaciones"])

# ============ MODELOS ============

class WelcomeEmailRequest(BaseModel):
    email: str
    company_name: str
    api_key: str
    plan: str

class LowCreditAlertRequest(BaseModel):
    email: str
    company_name: str
    queries_used: int
    queries_total: int
    plan: str

class MonthlyReportRequest(BaseModel):
    email: str
    company_name: str
    month: str  # Ej: "Marzo 2026"
    stats: Dict[str, Any]

class AdminNotificationRequest(BaseModel):
    ruc: str
    empresa: str
    plan: str
    email: str
    phone: Optional[str] = None
    nombre: Optional[str] = None
    score: Optional[str] = None

class EmailTestRequest(BaseModel):
    to_email: str
    template: str  # welcome, low_credit, admin_notification

# ============ ENDPOINTS ============

@router.post("/notifications/send-welcome")
async def send_welcome(request: WelcomeEmailRequest, x_admin_token: Optional[str] = Header(None)):
    """
    Enviar email de bienvenida a un nuevo cliente aprobado.
    Requiere token de admin.
    """
    # Verificar admin token
    from app.core.config import get_settings
    settings = get_settings()
    
    if x_admin_token != settings.ADMIN_TOKEN:
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "UNAUTHORIZED"}
        )
    
    result = await send_welcome_email(
        to_email=request.email,
        company_name=request.company_name,
        api_key=request.api_key,
        plan=request.plan
    )
    
    return result

@router.post("/notifications/send-low-credit")
async def send_low_credit(request: LowCreditAlertRequest, x_admin_token: Optional[str] = Header(None)):
    """
    Enviar alerta de crédito bajo a un cliente.
    Requiere token de admin.
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    if x_admin_token != settings.ADMIN_TOKEN:
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "UNAUTHORIZED"}
        )
    
    result = await send_low_credit_alert(
        to_email=request.email,
        company_name=request.company_name,
        queries_used=request.queries_used,
        queries_total=request.queries_total,
        plan=request.plan
    )
    
    return result

@router.post("/notifications/send-monthly-report")
async def send_monthly_report_endpoint(request: MonthlyReportRequest, x_admin_token: Optional[str] = Header(None)):
    """
    Enviar reporte mensual a un cliente.
    Requiere token de admin.
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    if x_admin_token != settings.ADMIN_TOKEN:
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "UNAUTHORIZED"}
        )
    
    result = await send_monthly_report(
        to_email=request.email,
        company_name=request.company_name,
        month=request.month,
        stats=request.stats
    )
    
    return result

@router.post("/notifications/notify-admin")
async def notify_admin(request: AdminNotificationRequest):
    """
    Notificar al admin sobre nueva postulación.
    Endpoint público - usado desde el formulario de landing.
    """
    applicant_data = {
        "ruc": request.ruc,
        "empresa": request.empresa,
        "plan": request.plan,
        "email": request.email,
        "phone": request.phone,
        "nombre": request.nombre,
        "score": request.score,
        "timestamp": datetime.now().isoformat()
    }
    
    result = await send_admin_notification(applicant_data)
    
    return result

@router.post("/notifications/test")
async def test_email(request: EmailTestRequest, x_admin_token: Optional[str] = Header(None)):
    """
    Endpoint de prueba para enviar emails de test.
    Requiere token de admin.
    """
    from app.core.config import get_settings
    settings = get_settings()
    
    if x_admin_token != settings.ADMIN_TOKEN:
        return JSONResponse(
            status_code=403,
            content={"success": False, "error": "UNAUTHORIZED"}
        )
    
    if request.template == "welcome":
        result = await send_welcome_email(
            to_email=request.to_email,
            company_name="Empresa de Prueba SAC",
            api_key="cz_test_123456789",
            plan="professional"
        )
    elif request.template == "low_credit":
        result = await send_low_credit_alert(
            to_email=request.to_email,
            company_name="Empresa de Prueba SAC",
            queries_used=95,
            queries_total=100,
            plan="starter"
        )
    elif request.template == "admin_notification":
        result = await send_admin_notification({
            "ruc": "20529400790",
            "empresa": "Constructora de Prueba SAC",
            "plan": "professional",
            "email": request.to_email,
            "phone": "51999999999",
            "nombre": "Juan Pérez",
            "score": "85.5"
        })
    else:
        return JSONResponse(
            status_code=400,
            content={"success": False, "error": "INVALID_TEMPLATE", "valid_templates": ["welcome", "low_credit", "admin_notification"]}
        )
    
    return result

@router.get("/notifications/status")
async def email_status():
    """
    Verificar estado del servicio de email.
    """
    return {
        "service": "SendGrid",
        "enabled": email_service.enabled,
        "from_email": email_service.sg.from_email if email_service.enabled else None,
        "timestamp": datetime.now().isoformat()
    }