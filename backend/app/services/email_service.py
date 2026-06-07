"""
SendGrid Email Service - Conflict Zero
Diseño UHNW (Ultra High Net Worth) - Negro/Dorado
"""
import os
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from sendgrid import SendGridAPIClient
    from sendgrid.helpers.mail import Mail, Email, Content, HtmlContent
    SENDGRID_AVAILABLE = True
except ImportError:
    SENDGRID_AVAILABLE = False
    print("[Email] SendGrid SDK no disponible, usando modo mock")

# Configuración
SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'contacto@czperu.com')
FROM_NAME = os.environ.get('FROM_NAME', 'Conflict Zero')
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'tiagomunoz10@icloud.com')

# Colores UHNW
UHNW_COLORS = {
    'black': '#0A0A0F',
    'dark_gray': '#141418',
    'medium_gray': '#1A1A1E',
    'light_gray': '#8A8A85',
    'cream': '#F5F5F0',
    'gold': '#C5A059',
    'gold_light': '#D4AF37',
}

class EmailService:
    """Servicio de email con diseño UHNW"""
    
    def __init__(self):
        self.sg = SendGridAPIClient(SENDGRID_API_KEY) if SENDGRID_AVAILABLE and SENDGRID_API_KEY else None
        self.enabled = self.sg is not None
    
    def _get_base_template(self, content: str, title: str) -> str:
        """Template base UHNW"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=Inter:wght@400;500;600&display=swap');
                
                body {{
                    margin: 0;
                    padding: 0;
                    background-color: {UHNW_COLORS['black']};
                    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                    color: {UHNW_COLORS['cream']};
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: {UHNW_COLORS['dark_gray']};
                    border: 1px solid {UHNW_COLORS['gold']};
                }}
                .header {{
                    background: linear-gradient(135deg, {UHNW_COLORS['black']} 0%, {UHNW_COLORS['medium_gray']} 100%);
                    padding: 40px 30px;
                    text-align: center;
                    border-bottom: 2px solid {UHNW_COLORS['gold']};
                }}
                .logo {{
                    font-family: 'Cormorant Garamond', Georgia, serif;
                    font-size: 28px;
                    font-weight: 700;
                    color: {UHNW_COLORS['gold']};
                    letter-spacing: 4px;
                    margin-bottom: 10px;
                }}
                .tagline {{
                    font-size: 11px;
                    color: {UHNW_COLORS['light_gray']};
                    text-transform: uppercase;
                    letter-spacing: 3px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .title {{
                    font-family: 'Cormorant Garamond', Georgia, serif;
                    font-size: 24px;
                    font-weight: 600;
                    color: {UHNW_COLORS['gold']};
                    margin-bottom: 20px;
                }}
                .text {{
                    font-size: 14px;
                    line-height: 1.8;
                    color: {UHNW_COLORS['cream']};
                    margin-bottom: 20px;
                }}
                .highlight {{
                    background-color: {UHNW_COLORS['medium_gray']};
                    padding: 20px;
                    border-left: 3px solid {UHNW_COLORS['gold']};
                    margin: 20px 0;
                }}
                .highlight-label {{
                    font-size: 11px;
                    color: {UHNW_COLORS['light_gray']};
                    text-transform: uppercase;
                    letter-spacing: 2px;
                    margin-bottom: 5px;
                }}
                .highlight-value {{
                    font-family: 'Cormorant Garamond', Georgia, serif;
                    font-size: 20px;
                    color: {UHNW_COLORS['gold']};
                    font-weight: 600;
                }}
                .cta-button {{
                    display: inline-block;
                    background-color: {UHNW_COLORS['gold']};
                    color: {UHNW_COLORS['black']} !important;
                    padding: 15px 30px;
                    text-decoration: none;
                    font-weight: 600;
                    font-size: 14px;
                    margin: 20px 0;
                    text-transform: uppercase;
                    letter-spacing: 2px;
                }}
                .footer {{
                    background-color: {UHNW_COLORS['black']};
                    padding: 30px;
                    text-align: center;
                    border-top: 1px solid {UHNW_COLORS['medium_gray']};
                }}
                .footer-text {{
                    font-size: 12px;
                    color: {UHNW_COLORS['light_gray']};
                }}
                .divider {{
                    height: 1px;
                    background: linear-gradient(90deg, transparent, {UHNW_COLORS['gold']}, transparent);
                    margin: 30px 0;
                }}
                .info-box {{
                    background-color: {UHNW_COLORS['medium_gray']};
                    padding: 15px 20px;
                    margin: 15px 0;
                }}
                .info-label {{
                    font-size: 10px;
                    color: {UHNW_COLORS['light_gray']};
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                .info-value {{
                    font-size: 14px;
                    color: {UHNW_COLORS['cream']};
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <div class="logo">CONFLICT ZERO</div>
                    <div class="tagline">Certificación de Cumplimiento Normativo</div>
                </div>
                <div class="content">
                    {content}
                </div>
                <div class="footer">
                    <div class="footer-text">
                        © 2026 Conflict Zero. Todos los derechos reservados.<br>
                        <a href="https://czperu.com" style="color: {UHNW_COLORS['gold']}; text-decoration: none;">czperu.com</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
    
    def send_welcome_email(self, to_email: str, company_name: str, api_key: str, plan: str) -> Dict[str, Any]:
        """Email de bienvenida cuando el admin aprueba al cliente"""
        
        content = f"""
        <div class="title">Bienvenido a Conflict Zero</div>
        
        <div class="text">
            Estimado equipo de <strong>{company_name}</strong>,<br><br>
            Su solicitud ha sido aprobada. Su empresa ahora forma parte del círculo exclusivo de empresas certificadas en cumplimiento normativo.
        </div>
        
        <div class="highlight">
            <div class="highlight-label">Plan Asignado</div>
            <div class="highlight-value">{plan.upper()}</div>
        </div>
        
        <div class="divider"></div>
        
        <div class="text">
            <strong>Su API Key:</strong>
        </div>
        
        <div class="info-box">
            <div class="info-value" style="font-family: monospace; font-size: 12px; word-break: break-all;">{api_key}</div>
        </div>
        
        <div class="text" style="font-size: 12px; color: {UHNW_COLORS['light_gray']};">
            Guarde esta clave en un lugar seguro. No la comparta.
        </div>
        
        <div class="divider"></div>
        
        <div class="text">
            Acceda a su dashboard para comenzar:
        </div>
        
        <a href="https://czperu.com/dashboard.html" class="cta-button">Ir al Dashboard</a>
        
        <div class="text" style="margin-top: 30px;">
            Para soporte técnico, contacte a:<br>
            <a href="mailto:soporte@czperu.com" style="color: {UHNW_COLORS['gold']}; text-decoration: none;">soporte@czperu.com</a>
        </div>
        """
        
        html_content = self._get_base_template(content, "Bienvenido a Conflict Zero")
        
        return self._send_email(
            to_email=to_email,
            subject="✓ Acceso Aprobado - Conflict Zero",
            html_content=html_content
        )
    
    def send_low_credit_alert(self, to_email: str, company_name: str, queries_used: int, queries_total: int, plan: str) -> Dict[str, Any]:
        """Alerta cuando quedan menos del 10% de consultas"""
        
        percentage = (queries_used / queries_total * 100) if queries_total > 0 else 0
        remaining = queries_total - queries_used
        
        content = f"""
        <div class="title">Alerta de Crédito</div>
        
        <div class="text">
            Estimado equipo de <strong>{company_name}</strong>,<br><br>
            Le informamos que está próximo a agotar su límite mensual de consultas.
        </div>
        
        <div class="highlight" style="border-left-color: #B87333;">
            <div class="highlight-label">Consultas Restantes</div>
            <div class="highlight-value" style="color: #B87333;">{remaining} de {queries_total}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Plan Actual</div>
            <div class="info-value">{plan.upper()}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Consultas Utilizadas</div>
            <div class="info-value">{queries_used} ({percentage:.1f}%)</div>
        </div>
        
        <div class="divider"></div>
        
        <div class="text">
            Para continuar validando RUCs sin interrupciones, considere actualizar su plan:
        </div>
        
        <a href="https://czperu.com/pricing.html" class="cta-button">Ver Planes</a>
        
        <div class="text" style="margin-top: 30px; font-size: 12px; color: {UHNW_COLORS['light_gray']};">
            Esta alerta se envía una vez al día cuando su crédito es inferior al 10%.
        </div>
        """
        
        html_content = self._get_base_template(content, "Alerta de Crédito - Conflict Zero")
        
        return self._send_email(
            to_email=to_email,
            subject="⚠ Crédito Bajo - Conflict Zero",
            html_content=html_content
        )
    
    def send_monthly_report(self, to_email: str, company_name: str, month: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Reporte mensual de actividad"""
        
        total_queries = stats.get('total_queries', 0)
        top_rucs = stats.get('top_rucs', [])
        avg_score = stats.get('avg_score', 0)
        new_sanctions = stats.get('new_sanctions', 0)
        
        top_rucs_html = ""
        for ruc_data in top_rucs[:5]:
            top_rucs_html += f"""
            <div class="info-box">
                <div class="info-value">{ruc_data.get('ruc')} - Score: {ruc_data.get('score')}</div>
            </div>
            """
        
        content = f"""
        <div class="title">Reporte Mensual</div>
        
        <div class="text">
            Estimado equipo de <strong>{company_name}</strong>,<br><br>
            Adjunto encontrará el resumen de actividad correspondiente a <strong>{month}</strong>.
        </div>
        
        <div class="highlight">
            <div class="highlight-label">Consultas Realizadas</div>
            <div class="highlight-value">{total_queries}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Score Promedio</div>
            <div class="info-value">{avg_score:.1f}/100</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Nuevas Sanciones Detectadas</div>
            <div class="info-value" style="color: {'#8B0000' if new_sanctions > 0 else UHNW_COLORS['gold']};">
                {new_sanctions}
            </div>
        </div>
        
        <div class="divider"></div>
        
        <div class="text">
            <strong>RUCs más consultados:</strong>
        </div>
        
        {top_rucs_html if top_rucs_html else '<div class="text" style="color: #666;">Sin consultas este mes</div>'}
        
        <div class="divider"></div>
        
        <a href="https://czperu.com/dashboard.html" class="cta-button">Ver Dashboard</a>
        """
        
        html_content = self._get_base_template(content, f"Reporte {month} - Conflict Zero")
        
        return self._send_email(
            to_email=to_email,
            subject=f"📊 Reporte {month} - Conflict Zero",
            html_content=html_content
        )
    
    def send_admin_notification(self, applicant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Notificar al admin sobre nueva postulación"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[Send Admin Notification] ADMIN_EMAIL value: {ADMIN_EMAIL}")
        
        content = f"""
        <div class="title" style="color: #8B0000;">🚨 Nueva Postulación</div>
        
        <div class="text">
            Una nueva empresa ha solicitado acceso a Conflict Zero y requiere su aprobación.
        </div>
        
        <div class="info-box">
            <div class="info-label">Empresa</div>
            <div class="info-value">{applicant_data.get('empresa', 'N/A')}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">RUC</div>
            <div class="info-value">{applicant_data.get('ruc', 'N/A')}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Plan Solicitado</div>
            <div class="info-value" style="color: {UHNW_COLORS['gold']};">{applicant_data.get('plan', 'N/A').upper()}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Score Legal</div>
            <div class="info-value">{applicant_data.get('score', 'N/A')}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Email de Contacto</div>
            <div class="info-value">{applicant_data.get('email', 'N/A')}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Teléfono</div>
            <div class="info-value">{applicant_data.get('phone', 'No proporcionado')}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Solicitante</div>
            <div class="info-value">{applicant_data.get('nombre', 'No proporcionado')}</div>
        </div>
        
        <div class="divider"></div>
        
        <a href="https://czperu.com/admin-v3.html" class="cta-button">Ir al Panel Admin</a>
        """
        
        html_content = self._get_base_template(content, "Nueva Postulación - Conflict Zero")
        
        return self._send_email(
            to_email=ADMIN_EMAIL,
            subject=f"🚨 Nueva Postulación: {applicant_data.get('empresa', 'Unknown')}",
            html_content=html_content
        )
    
    async def send_supplier_alert_email(
        self,
        to_email: str,
        company_name: str,
        supplier_ruc: str,
        supplier_name: str,
        change_type: str,
        previous_status: str,
        new_status: str,
        severity: str
    ) -> Dict[str, Any]:
        """Alerta cuando un proveedor cambia de estado (high/critical)"""
        
        severity_colors = {
            'critical': '#8B0000',
            'high': '#B87333',
            'medium': UHNW_COLORS['gold'],
            'low': UHNW_COLORS['light_gray']
        }
        
        severity_labels = {
            'critical': 'CRÍTICO',
            'high': 'ALTO',
            'medium': 'MEDIO',
            'low': 'BAJO'
        }
        
        color = severity_colors.get(severity, UHNW_COLORS['gold'])
        label = severity_labels.get(severity, 'ALERTA')
        
        content = f"""
        <div class="title" style="color: {color};">⚠ Alerta de Proveedor</div>
        
        <div class="text">
            Estimado equipo de <strong>{company_name}</strong>,<br><br>
            Le informamos que uno de sus proveedores ha cambiado de estado. Recomendamos revisar la relación comercial.
        </div>
        
        <div class="highlight" style="border-left-color: {color};">
            <div class="highlight-label">Nivel de Riesgo</div>
            <div class="highlight-value" style="color: {color};">{label}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Proveedor</div>
            <div class="info-value">{supplier_name} (RUC: {supplier_ruc})</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Tipo de Cambio</div>
            <div class="info-value">{change_type}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Estado Anterior</div>
            <div class="info-value">{previous_status}</div>
        </div>
        
        <div class="info-box">
            <div class="info-label">Estado Actual</div>
            <div class="info-value" style="color: {color};">{new_status}</div>
        </div>
        
        <div class="divider"></div>
        
        <div class="text">
            Recomendamos verificar el estado actual de este proveedor en su dashboard:
        </div>
        
        <a href="https://czperu.com/dashboard.html" class="cta-button">Ver Dashboard</a>
        
        <div class="text" style="margin-top: 30px; font-size: 12px; color: {UHNW_COLORS['light_gray']};">
            Esta alerta se genera automáticamente cuando detectamos cambios significativos en el estado de sus proveedores.
        </div>
        """
        
        html_content = self._get_base_template(content, f"Alerta de Proveedor - {supplier_name}")
        
        return self._send_email(
            to_email=to_email,
            subject=f"⚠ Alerta {label}: {supplier_name} - Conflict Zero",
            html_content=html_content
        )

    def _send_email(self, to_email: str, subject: str, html_content: str) -> Dict[str, Any]:
        """Enviar email via SendGrid"""
        
        if not self.enabled:
            print(f"[Email] Modo mock - Email a {to_email}: {subject}")
            return {
                "success": True,
                "mock": True,
                "to": to_email,
                "subject": subject
            }
        
        try:
            message = Mail(
                from_email=Email(FROM_EMAIL, FROM_NAME),
                to_emails=to_email,
                subject=subject,
                html_content=html_content
            )
            
            response = self.sg.send(message)
            
            return {
                "success": 200 <= response.status_code < 300,
                "status_code": response.status_code,
                "to": to_email,
                "subject": subject,
                "message_id": response.headers.get('X-Message-Id', 'unknown')
            }
            
        except Exception as e:
            print(f"[Email] Error enviando a {to_email}: {e}")
            return {
                "success": False,
                "error": str(e),
                "to": to_email,
                "subject": subject
            }

# Instancia global
email_service = EmailService()

# Exportar funciones helper
async def send_welcome_email(to_email: str, company_name: str, api_key: str, plan: str):
    return email_service.send_welcome_email(to_email, company_name, api_key, plan)

async def send_low_credit_alert(to_email: str, company_name: str, queries_used: int, queries_total: int, plan: str):
    return email_service.send_low_credit_alert(to_email, company_name, queries_used, queries_total, plan)

async def send_monthly_report(to_email: str, company_name: str, month: str, stats: Dict[str, Any]):
    return email_service.send_monthly_report(to_email, company_name, month, stats)

async def send_supplier_alert_email(to_email: str, company_name: str, supplier_ruc: str, supplier_name: str, change_type: str, previous_status: str, new_status: str, severity: str):
    return email_service.send_supplier_alert_email(to_email, company_name, supplier_ruc, supplier_name, change_type, previous_status, new_status, severity)

async def send_admin_notification(applicant_data: Dict[str, Any]):
    return email_service.send_admin_notification(applicant_data)

__all__ = [
    'EmailService',
    'email_service',
    'send_welcome_email',
    'send_low_credit_alert',
    'send_monthly_report',
    'send_supplier_alert_email',
    'send_admin_notification'
]