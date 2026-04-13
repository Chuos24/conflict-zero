"""
Servicio de envío de emails para Conflict Zero
Soporta: SendGrid, AWS SES, SMTP
"""
import os
import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Intentar importar librerías opcionales
try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, Content
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False

try:
    import boto3
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

try:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    SMTP_AVAILABLE = True
except ImportError:
    SMTP_AVAILABLE = False


class EmailService:
    """Servicio de envío de emails con fallback entre proveedores"""
    
    def __init__(self):
        self.provider = self._detect_provider()
        self.from_email = os.getenv("EMAIL_FROM", "contacto@czperu.com")
        self.from_name = os.getenv("EMAIL_FROM_NAME", "Conflict Zero")
        
    def _detect_provider(self) -> str:
        """Detecta qué proveedor de email está configurado"""
        if os.getenv("SENDGRID_API_KEY"):
            return "sendgrid"
        elif os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("EMAIL_USE_SES"):
            return "ses"
        elif os.getenv("SMTP_HOST"):
            return "smtp"
        else:
            return "none"
    
    def _get_welcome_template(self, email: str, temp_password: str, full_name: str, plan: str) -> str:
        """Template HTML para email de bienvenida"""
        plan_names = {
            "starter": "Starter",
            "essential": "Essential", 
            "professional": "Professional",
            "enterprise": "Enterprise"
        }
        plan_name = plan_names.get(plan, plan)
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Bienvenido a Conflict Zero</title>
            <style>
                body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0a; margin: 0; padding: 0; color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .logo {{ text-align: center; margin-bottom: 30px; }}
                .logo-text {{ font-family: 'Cormorant Garamond', serif; font-size: 28px; color: #c9a961; letter-spacing: 2px; }}
                .card {{ background: #141414; border: 1px solid #2a2a2a; border-radius: 16px; padding: 40px; }}
                h1 {{ font-family: 'Cormorant Garamond', serif; font-size: 24px; font-weight: 500; color: #f5f5f5; margin-bottom: 20px; }}
                p {{ color: #888; line-height: 1.6; margin-bottom: 16px; font-size: 15px; }}
                .credentials {{ background: #0a0a0a; border: 1px solid #c9a961; border-radius: 8px; padding: 20px; margin: 24px 0; }}
                .credentials-label {{ color: #c9a961; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }}
                .credentials-value {{ color: #f5f5f5; font-family: monospace; font-size: 14px; word-break: break-all; }}
                .btn {{ display: inline-block; background: #c9a961; color: #0a0a0a; text-decoration: none; padding: 14px 28px; border-radius: 8px; font-weight: 600; margin: 20px 0; }}
                .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #2a2a2a; color: #555; font-size: 13px; }}
                .highlight {{ color: #c9a961; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <div class="logo-text">CONFLICT ZERO</div>
                </div>
                
                <div class="card">
                    <h1>¡Bienvenido, {full_name}!</h1>
                    
                    <p>Su solicitud de acceso a <span class="highlight">Conflict Zero</span> ha sido aprobada.</p>
                    
                    <p>Plan seleccionado: <strong class="highlight">{plan_name}</strong></p>
                    
                    <p>A continuación encontrará sus credenciales de acceso:</p>
                    
                    <div class="credentials">
                        <div class="credentials-label">Correo electrónico</div>
                        <div class="credentials-value">{email}</div>
                    </div>
                    
                    <div class="credentials">
                        <div class="credentials-label">Contraseña temporal</div>
                        <div class="credentials-value">{temp_password}</div>
                    </div>
                    
                    <p style="color: #dc3545; font-size: 13px;">⚠️ Por seguridad, cambie su contraseña después del primer inicio de sesión.</p>
                    
                    <center>
                        <a href="https://czperu.com/login.html" class="btn">Acceder a mi cuenta</a>
                    </center>
                    
                    <p style="margin-top: 30px; font-size: 13px; color: #666;">
                        Si tiene alguna pregunta, responda a este correo o contacte a nuestro equipo de soporte.
                    </p>
                </div>
                
                <div class="footer">
                    <p>© 2026 Conflict Zero. Todos los derechos reservados.</p>
                    <p>Este es un correo automático, por favor no responda directamente.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def _get_notification_template(self, subject: str, message: str) -> str:
        """Template HTML genérico para notificaciones"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{subject}</title>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0a0a0a; margin: 0; padding: 0; color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
                .card {{ background: #141414; border: 1px solid #2a2a2a; border-radius: 16px; padding: 40px; }}
                h1 {{ font-family: 'Cormorant Garamond', serif; color: #c9a961; }}
                p {{ color: #888; line-height: 1.6; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>{subject}</h1>
                    <p>{message}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> bool:
        """Envía un email usando el proveedor configurado"""
        if self.provider == "none":
            logger.warning("No hay proveedor de email configurado. Email no enviado.")
            logger.info(f"[EMAIL SIMULADO] Para: {to_email} | Asunto: {subject}")
            return False
        
        try:
            if self.provider == "sendgrid":
                return self._send_sendgrid(to_email, subject, html_content, text_content)
            elif self.provider == "ses":
                return self._send_ses(to_email, subject, html_content, text_content)
            elif self.provider == "smtp":
                return self._send_smtp(to_email, subject, html_content, text_content)
            else:
                return False
        except Exception as e:
            logger.error(f"Error enviando email: {e}")
            return False
    
    def _send_sendgrid(self, to_email: str, subject: str, html_content: str, text_content: Optional[str]) -> bool:
        """Envía email usando SendGrid"""
        if not SENDGRID_AVAILABLE:
            logger.error("Librería sendgrid no instalada")
            return False
        
        sg = sendgrid.SendGridAPIClient(api_key=os.getenv("SENDGRID_API_KEY"))
        
        message = Mail(
            from_email=Email(self.from_email, self.from_name),
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        if text_content:
            message.content = Content("text/plain", text_content)
        
        response = sg.send(message)
        
        success = response.status_code in [200, 201, 202]
        if success:
            logger.info(f"Email enviado vía SendGrid a {to_email}")
        else:
            logger.error(f"Error SendGrid: {response.status_code} - {response.body}")
        
        return success
    
    def _send_ses(self, to_email: str, subject: str, html_content: str, text_content: Optional[str]) -> bool:
        """Envía email usando AWS SES"""
        if not AWS_AVAILABLE:
            logger.error("Librería boto3 no instalada")
            return False
        
        client = boto3.client(
            'ses',
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        
        response = client.send_email(
            Source=f"{self.from_name} <{self.from_email}>",
            Destination={'ToAddresses': [to_email]},
            Message={
                'Subject': {'Data': subject},
                'Body': {
                    'Html': {'Data': html_content},
                    'Text': {'Data': text_content or ''}
                }
            }
        )
        
        success = 'MessageId' in response
        if success:
            logger.info(f"Email enviado vía SES a {to_email}")
        return success
    
    def _send_smtp(self, to_email: str, subject: str, html_content: str, text_content: Optional[str]) -> bool:
        """Envía email usando SMTP"""
        if not SMTP_AVAILABLE:
            logger.error("Módulo smtplib no disponible")
            return False
        
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        password = os.getenv("SMTP_PASSWORD")
        use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email
        
        if text_content:
            msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        with smtplib.SMTP(host, port) as server:
            if use_tls:
                server.starttls()
            if user and password:
                server.login(user, password)
            server.send_message(msg)
        
        logger.info(f"Email enviado vía SMTP a {to_email}")
        return True
    
    def send_welcome_email(self, email: str, temp_password: str, full_name: str, plan: str) -> bool:
        """Envía email de bienvenida con credenciales"""
        subject = "Bienvenido a Conflict Zero - Credenciales de acceso"
        html_content = self._get_welcome_template(email, temp_password, full_name, plan)
        text_content = f"""
Bienvenido a Conflict Zero, {full_name}!

Su solicitud ha sido aprobada.

Credenciales de acceso:
- Email: {email}
- Contraseña temporal: {temp_password}

Acceda en: https://czperu.com/login.html

Cambie su contraseña después del primer inicio de sesión.

Conflict Zero Team
        """
        return self.send_email(email, subject, html_content, text_content)
    
    def send_notification(self, to_email: str, subject: str, message: str) -> bool:
        """Envía notificación genérica"""
        html_content = self._get_notification_template(subject, message)
        return self.send_email(to_email, subject, html_content, message)

    def send_admin_registration_notification(
        self,
        admin_email: str,
        user_email: str,
        user_name: str,
        user_company: str,
        user_ruc: str,
        plan: str
    ) -> bool:
        """Envía notificación al admin sobre un nuevo registro"""
        subject = f"🚀 Nuevo registro - {user_company}"
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Inter, sans-serif; background: #0a0a0a; color: #f5f5f5; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background: #141414; border: 1px solid #2a2a2a; border-radius: 16px; padding: 40px;">
            <h2 style="color: #c9a961; font-family: Cormorant Garamond, serif;">🚀 Nuevo Registro Conflict Zero</h2>
            <p><strong>Empresa:</strong> {user_company}</p>
            <p><strong>Contacto:</strong> {user_name}</p>
            <p><strong>Email:</strong> {user_email}</p>
            <p><strong>RUC:</strong> {user_ruc}</p>
            <p><strong>Plan:</strong> {plan.upper()}</p>
            <p style="color: #666; margin-top: 20px;">Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
        </body>
        </html>
        """
        text_content = f"""Nuevo registro en Conflict Zero:
Empresa: {user_company}
Contacto: {user_name}
Email: {user_email}
RUC: {user_ruc}
Plan: {plan.upper()}
"""
        return self.send_email(admin_email, subject, html_content, text_content)


# Singleton
def get_email_service() -> EmailService:
    return EmailService()
