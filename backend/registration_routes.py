"""
Extension de endpoints para Conflict Zero
Agrega el endpoint de notificacion de registro
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

router = APIRouter()

ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'tiagomunoz10@icloud.com')

class RegistrationNotificationRequest(BaseModel):
    ruc: str
    razon_social: str
    representante: str
    email: str
    telefono: str
    cargo: str
    plan_solicitado: str
    score: Optional[str] = None
    tier: Optional[str] = None

@router.post("/admin/notify-registration")
async def notify_registration(request: RegistrationNotificationRequest):
    """
    Notificar al administrador sobre nuevo registro de cliente
    Envía email con los datos del cliente para creación de cuenta
    """
    try:
        print(f"[REGISTRO] Nueva solicitud: {request.razon_social} (RUC: {request.ruc})")
        
        # Email destino (admin)
        dest_email = ADMIN_EMAIL
        
        # Intentar enviar email usando el servicio de email existente
        email_sent = False
        try:
            import httpx
            
            # Usar SendGrid si está configurado
            sendgrid_key = os.environ.get('SENDGRID_API_KEY', '')
            
            if sendgrid_key:
                headers = {
                    "Authorization": f"Bearer {sendgrid_key}",
                    "Content-Type": "application/json"
                }
                
                email_data = {
                    "personalizations": [{
                        "to": [{"email": dest_email}]
                    }],
                    "from": {"email": "noreply@czperu.com", "name": "Conflict Zero"},
                    "subject": f"Nueva Solicitud de Registro - {request.razon_social}",
                    "content": [{
                        "type": "text/plain",
                        "value": f"""NUEVA SOLICITUD DE REGISTRO - CONFLICT ZERO

DATOS DE LA EMPRESA:
• Razón Social: {request.razon_social}
• RUC: {request.ruc}
• Score Legal: {request.score or 'N/A'}/100
• Sello Asignado: {request.tier or 'N/A'}

DATOS DEL REPRESENTANTE:
• Nombre: {request.representante}
• Cargo: {request.cargo}
• Email: {request.email}
• Teléfono: {request.telefono}

PLAN SOLICITADO:
• {request.plan_solicitado.upper()}

ACCIÓN REQUERIDA:
Crear cuenta de usuario en el panel de administración.
URL: https://www.czperu.com/admin-v3.html

--
Conflict Zero - Estándar de Verificación Institucional
"""
                    }]
                }
                
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers=headers,
                        json=email_data
                    )
                    if resp.status_code == 202:
                        email_sent = True
                        print(f"[EMAIL] Enviado a {dest_email}")
                    else:
                        print(f"[EMAIL] Error: {resp.status_code} - {resp.text}")
            else:
                print("[EMAIL] SENDGRID_API_KEY no configurado")
                
        except Exception as e:
            print(f"[EMAIL] Error enviando: {e}")
        
        return {
            "success": True,
            "message": "Solicitud registrada" + (" y email enviado" if email_sent else ""),
            "data": {
                "ruc": request.ruc,
                "razon_social": request.razon_social,
                "plan": request.plan_solicitado,
                "email_sent": email_sent,
                "admin_email": dest_email
            }
        }
        
    except Exception as e:
        print(f"[REGISTRO] Error: {e}")
        return {
            "success": True,
            "message": "Solicitud registrada (notificación pendiente)",
            "data": {
                "ruc": request.ruc,
                "razon_social": request.razon_social,
                "plan": request.plan_solicitado,
                "email_sent": False
            }
        }
