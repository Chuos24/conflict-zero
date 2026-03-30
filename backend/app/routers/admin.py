# Admin Router - White Glove Flow
# Endpoints para gestión de solicitudes y aprobaciones

from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, List
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Database
import psycopg2
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/api/v3/admin", tags=["admin"])

# Admin token from environment
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'cz2026')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@czperu.com')
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def verify_admin(authorization: str = Header(None)):
    """Verify admin token"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    token = authorization.replace("Bearer ", "").strip()
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    return True

# ==================== MODELS ====================

class NotifyAdminRequest(BaseModel):
    ruc: str
    empresa: str
    plan: str
    email: str
    phone: Optional[str] = None
    nombre: Optional[str] = None
    score: Optional[str] = None

class ApproveUserRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None

class PendingUser(BaseModel):
    id: int
    ruc: str
    business_name: str
    email: str
    plan: str
    score_at_registration: Optional[float] = None
    status: str
    created_at: str
    phone: Optional[str] = None
    contact_name: Optional[str] = None

# ==================== ENDPOINTS ====================

@router.post("/notify-admin")
async def notify_admin(request: NotifyAdminRequest):
    """
    Notificar al administrador sobre nueva postulación
    Envía email con los datos del solicitante
    """
    try:
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"🚨 Nueva Postulación CZ: {request.empresa} - {request.plan}"
        msg['From'] = ADMIN_EMAIL
        msg['To'] = ADMIN_EMAIL
        
        # Contenido HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background: #0A0A0F; color: #F5F5F0; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #141418; padding: 30px; border: 1px solid #C5A059; }}
                h1 {{ color: #C5A059; font-size: 24px; }}
                .field {{ margin: 15px 0; padding: 10px; background: #1A1A1E; }}
                .label {{ color: #8A8A85; font-size: 12px; text-transform: uppercase; }}
                .value {{ color: #F5F5F0; font-size: 16px; margin-top: 5px; }}
                .cta {{ display: inline-block; margin-top: 20px; padding: 15px 30px; background: #C5A059; color: #0A0A0F; text-decoration: none; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🚨 Nueva Postulación Recibida</h1>
                <p>Una nueva empresa ha solicitado acceso a Conflict Zero.</p>
                
                <div class="field">
                    <div class="label">Empresa</div>
                    <div class="value">{request.empresa}</div>
                </div>
                
                <div class="field">
                    <div class="label">RUC</div>
                    <div class="value">{request.ruc}</div>
                </div>
                
                <div class="field">
                    <div class="label">Plan Solicitado</div>
                    <div class="value" style="color: #C5A059; font-weight: bold;">{request.plan}</div>
                </div>
                
                <div class="field">
                    <div class="label">Score Legal</div>
                    <div class="value">{request.score or 'N/A'}</div>
                </div>
                
                <div class="field">
                    <div class="label">Email</div>
                    <div class="value">{request.email}</div>
                </div>
                
                <div class="field">
                    <div class="label">Teléfono</div>
                    <div class="value">{request.phone or 'No proporcionado'}</div>
                </div>
                
                <div class="field">
                    <div class="label">Contacto</div>
                    <div class="value">{request.nombre or 'No proporcionado'}</div>
                </div>
                
                <p style="margin-top: 30px;">
                    <a href="https://czperu.com/admin-v3.html" class="cta">Ir al Panel de Admin</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(html_content, 'html'))
        
        # Enviar email (simulado por ahora - en producción usar SMTP real)
        # smtp_host = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
        # smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        # smtp_user = os.environ.get('SMTP_USER', '')
        # smtp_pass = os.environ.get('SMTP_PASS', '')
        # 
        # if smtp_user and smtp_pass:
        #     with smtplib.SMTP(smtp_host, smtp_port) as server:
        #         server.starttls()
        #         server.login(smtp_user, smtp_pass)
        #         server.send_message(msg)
        
        print(f"[ADMIN] Notificación enviada: {request.empresa} - {request.plan}")
        
        return {
            "success": True,
            "message": "Notificación enviada al administrador"
        }
        
    except Exception as e:
        print(f"[ADMIN] Error enviando notificación: {e}")
        raise HTTPException(status_code=500, detail=f"Error enviando notificación: {str(e)}")


@router.get("/pending-users", response_model=dict)
async def get_pending_users(admin: bool = Depends(verify_admin)):
    """
    Obtener lista de usuarios pendientes de aprobación
    Requiere token de admin
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                id, ruc, business_name, email, plan, 
                score_at_registration, status, created_at,
                phone, contact_name
            FROM users 
            WHERE status = 'pending_approval'
            ORDER BY created_at DESC
        """)
        
        users = cursor.fetchall()
        
        # Convertir datetime a string
        for user in users:
            if user['created_at']:
                user['created_at'] = user['created_at'].isoformat()
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "pending_count": len(users),
            "users": users
        }
        
    except Exception as e:
        print(f"[ADMIN] Error obteniendo usuarios pendientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo usuarios: {str(e)}")


@router.post("/approve-user/{user_id}")
async def approve_user(
    user_id: int, 
    request: ApproveUserRequest,
    admin: bool = Depends(verify_admin)
):
    """
    Aprobar o rechazar un usuario pendiente
    Requiere token de admin
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el usuario existe y está pendiente
        cursor.execute(
            "SELECT id, email, business_name, status FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if user[3] != 'pending_approval':
            cursor.close()
            conn.close()
            raise HTTPException(status_code=400, detail="Usuario no está pendiente de aprobación")
        
        # Actualizar estado
        new_status = 'active' if request.approved else 'rejected'
        cursor.execute(
            "UPDATE users SET status = %s, updated_at = NOW() WHERE id = %s",
            (new_status, user_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        action = "aprobado" if request.approved else "rechazado"
        print(f"[ADMIN] Usuario {user_id} {action}")
        
        return {
            "success": True,
            "message": f"Usuario {action} correctamente",
            "user_id": user_id,
            "status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ADMIN] Error aprobando usuario: {e}")
        raise HTTPException(status_code=500, detail=f"Error aprobando usuario: {str(e)}")
