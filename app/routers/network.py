"""
Mi Red / Supplier Watchlist - Conflict Zero API
Monitoreo continuo de proveedores con alertas automáticas.
"""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, SupplierAlert, CompanySnapshot, VerificationRequest
from app.services.email import get_email_service
from app.services.scoring import scoring_engine

router = APIRouter(prefix="/network", tags=["Mi Red"])

# ============================================================================
# SCHEMAS
# ============================================================================

class AddSupplierRequest(BaseModel):
    ruc: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    supplier_name: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = Field(default=None, max_length=500)

class SupplierResponse(BaseModel):
    id: str
    ruc: str
    supplier_name: Optional[str]
    risk_level: str
    score: int
    added_at: datetime
    last_checked: Optional[datetime]
    notes: Optional[str]

class AlertResponse(BaseModel):
    id: str
    supplier_ruc: str
    supplier_name: Optional[str]
    change_type: str
    previous_status: Optional[str]
    new_status: Optional[str]
    severity: str
    is_read: bool
    created_at: datetime

class MarkReadRequest(BaseModel):
    alert_ids: List[str]

# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post(
    "/add",
    summary="Agregar proveedor a Mi Red",
    description="Agrega un RUC a la lista de monitoreo del usuario."
)
async def add_supplier(
    data: AddSupplierRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Agrega un proveedor a la watchlist del usuario.
    
    - **ruc**: RUC de 11 dígitos del proveedor
    - **supplier_name**: (opcional) Nombre del proveedor
    - **notes**: (opcional) Notas personalizadas
    """
    # Verificar si ya existe en la watchlist
    existing = db.query(CompanySnapshot).filter(
        CompanySnapshot.ruc == data.ruc,
        CompanySnapshot.source_api == "watchlist"
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Este RUC ya está en tu red de monitoreo"
        )
    
    # Obtener datos actuales del proveedor
    score_result = scoring_engine.calculate_total_score(
        ruc=data.ruc,
        razon_social=data.supplier_name or "",
        estado="ACTIVO",
        condicion="HABIDO"
    )
    
    # Crear snapshot inicial
    snapshot = CompanySnapshot(
        ruc=data.ruc,
        supplier_name=data.supplier_name or score_result.get("company_name", ""),
        score_calculado=score_result.get("total_score", 50),
        osce_sanciones_count=score_result.get("osce_analysis", {}).get("cantidad", 0),
        osce_sanciones_vigentes=score_result.get("osce_analysis", {}).get("sanciones_vigentes", 0),
        tce_sanciones_count=score_result.get("rnp_tce_analysis", {}).get("cantidad_sanciones", 0),
        source_api="watchlist",
        raw_data_hash=str(hash(str(score_result)))  # Para detectar cambios
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    return {
        "success": True,
        "message": f"Proveedor {data.ruc} agregado a tu red",
        "supplier": {
            "id": snapshot.id,
            "ruc": snapshot.ruc,
            "supplier_name": snapshot.supplier_name,
            "score": snapshot.score_calculado,
            "risk_level": score_result.get("risk_level", "medium"),
            "added_at": snapshot.created_at
        }
    }


@router.delete(
    "/{ruc}",
    summary="Quitar proveedor de Mi Red",
    description="Elimina un RUC de la lista de monitoreo."
)
async def remove_supplier(
    ruc: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Elimina un proveedor de la watchlist del usuario."""
    # Eliminar snapshots del watchlist para este RUC
    snapshots = db.query(CompanySnapshot).filter(
        CompanySnapshot.ruc == ruc,
        CompanySnapshot.source_api == "watchlist"
    ).all()
    
    if not snapshots:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proveedor no encontrado en tu red"
        )
    
    for snapshot in snapshots:
        db.delete(snapshot)
    
    # También eliminar alertas asociadas
    alerts = db.query(SupplierAlert).filter(
        SupplierAlert.supplier_ruc == ruc,
        SupplierAlert.user_id == current_user.id
    ).all()
    
    for alert in alerts:
        db.delete(alert)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Proveedor {ruc} eliminado de tu red"
    }


@router.get(
    "/",
    summary="Listar proveedores monitoreados",
    description="Obtiene todos los RUCs en la red de monitoreo del usuario."
)
async def list_suppliers(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retorna la lista de proveedores monitoreados."""
    # Obtener snapshots más recientes por RUC
    from sqlalchemy import func
    
    subquery = db.query(
        CompanySnapshot.ruc,
        func.max(CompanySnapshot.created_at).label("max_date")
    ).filter(
        CompanySnapshot.source_api == "watchlist"
    ).group_by(
        CompanySnapshot.ruc
    ).subquery()
    
    snapshots = db.query(CompanySnapshot).join(
        subquery,
        (CompanySnapshot.ruc == subquery.c.ruc) &
        (CompanySnapshot.created_at == subquery.c.max_date)
    ).filter(
        CompanySnapshot.source_api == "watchlist"
    ).all()
    
    suppliers = []
    for snapshot in snapshots:
        # Determinar nivel de riesgo basado en score
        score = snapshot.score_calculado or 50
        if score >= 80:
            risk_level = "low"
        elif score >= 60:
            risk_level = "medium"
        elif score >= 40:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        suppliers.append({
            "id": snapshot.id,
            "ruc": snapshot.ruc,
            "supplier_name": snapshot.supplier_name,
            "risk_level": risk_level,
            "score": score,
            "added_at": snapshot.created_at,
            "last_checked": snapshot.snapshot_date,
            "osce_sanciones": snapshot.osce_sanciones_count or 0,
            "tce_sanciones": snapshot.tce_sanciones_count or 0
        })
    
    return {
        "suppliers": suppliers,
        "total": len(suppliers),
        "alerts_unread": db.query(SupplierAlert).filter(
            SupplierAlert.user_id == current_user.id,
            SupplierAlert.is_read == False
        ).count()
    }


@router.get(
    "/alerts",
    summary="Ver alertas",
    description="Obtiene las alertas de cambios detectados en proveedores monitoreados."
)
async def get_alerts(
    unread_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retorna las alertas del usuario."""
    query = db.query(SupplierAlert).filter(
        SupplierAlert.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(SupplierAlert.is_read == False)
    
    alerts = query.order_by(desc(SupplierAlert.created_at)).limit(50).all()
    
    return {
        "alerts": [
            {
                "id": alert.id,
                "supplier_ruc": alert.supplier_ruc,
                "supplier_name": alert.supplier_name,
                "change_type": alert.change_type,
                "previous_status": alert.previous_status,
                "new_status": alert.new_status,
                "severity": alert.severity,
                "is_read": alert.is_read,
                "email_sent": alert.email_sent,
                "created_at": alert.created_at
            }
            for alert in alerts
        ],
        "total": len(alerts),
        "unread_count": db.query(SupplierAlert).filter(
            SupplierAlert.user_id == current_user.id,
            SupplierAlert.is_read == False
        ).count()
    }


@router.patch(
    "/alerts/{alert_id}/read",
    summary="Marcar alerta como leída",
    description="Marca una alerta específica como leída."
)
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marca una alerta como leída."""
    alert = db.query(SupplierAlert).filter(
        SupplierAlert.id == alert_id,
        SupplierAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta no encontrada"
        )
    
    alert.is_read = True
    db.commit()
    
    return {
        "success": True,
        "message": "Alerta marcada como leída"
    }


@router.post(
    "/alerts/mark-read",
    summary="Marcar múltiples alertas como leídas",
    description="Marca múltiples alertas como leídas de una vez."
)
async def mark_multiple_alerts_read(
    data: MarkReadRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Marca múltiples alertas como leídas."""
    updated = db.query(SupplierAlert).filter(
        SupplierAlert.id.in_(data.alert_ids),
        SupplierAlert.user_id == current_user.id
    ).update({"is_read": True}, synchronize_session=False)
    
    db.commit()
    
    return {
        "success": True,
        "message": f"{updated} alertas marcadas como leídas"
    }


# ============================================================================
# FUNCIONES INTERNAS (usadas por cron job)
# ============================================================================

def check_supplier_changes(db: Session, ruc: str) -> list:
    """
    Verifica si hay cambios en un proveedor monitoreado.
    Retorna lista de alertas detectadas.
    """
    from sqlalchemy import func
    
    alerts = []
    
    # Obtener snapshot más reciente
    latest_snapshot = db.query(CompanySnapshot).filter(
        CompanySnapshot.ruc == ruc,
        CompanySnapshot.source_api == "watchlist"
    ).order_by(
        desc(CompanySnapshot.created_at)
    ).first()
    
    if not latest_snapshot:
        return alerts
    
    # Obtener datos actuales
    current_data = scoring_engine.calculate_total_score(
        ruc=ruc,
        razon_social="",
        estado="ACTIVO",
        condicion="HABIDO"
    )
    current_hash = str(hash(str(current_data)))
    
    # Si el hash es diferente, hay cambios
    if latest_snapshot.raw_data_hash != current_hash:
        # Detectar qué cambió específicamente
        old_score = latest_snapshot.score_calculado or 50
        new_score = current_data.get("total_score", 50)
        
        # Cambio en score significativo (>10 puntos)
        if abs(new_score - old_score) >= 10:
            severity = "high" if new_score < old_score else "medium"
            alerts.append({
                "change_type": "score_change",
                "previous_status": f"Score: {old_score}",
                "new_status": f"Score: {new_score}",
                "severity": severity
            })
        
        # Nueva sanción OSCE
        old_osce = latest_snapshot.osce_sanciones_vigentes or 0
        new_osce = current_data.get("osce_analysis", {}).get("sanciones_vigentes", 0)
        if new_osce > old_osce:
            alerts.append({
                "change_type": "osce_new_sanction",
                "previous_status": f"Sanciones vigentes: {old_osce}",
                "new_status": f"Sanciones vigentes: {new_osce}",
                "severity": "critical"
            })
        
        # Nueva sanción TCE
        old_tce = latest_snapshot.tce_sanciones_count or 0
        new_tce = current_data.get("rnp_tce_analysis", {}).get("cantidad_sanciones", 0)
        if new_tce > old_tce:
            alerts.append({
                "change_type": "tce_new_sanction",
                "previous_status": f"Sanciones TCE: {old_tce}",
                "new_status": f"Sanciones TCE: {new_tce}",
                "severity": "critical"
            })
        
        # Actualizar snapshot
        latest_snapshot.score_calculado = new_score
        latest_snapshot.osce_sanciones_count = current_data.get("osce_analysis", {}).get("cantidad", 0)
        latest_snapshot.osce_sanciones_vigentes = current_data.get("osce_analysis", {}).get("sanciones_vigentes", 0)
        latest_snapshot.tce_sanciones_count = current_data.get("rnp_tce_analysis", {}).get("cantidad_sanciones", 0)
        latest_snapshot.raw_data_hash = current_hash
        latest_snapshot.snapshot_date = datetime.now(timezone.utc)
        
        db.commit()
    
    return alerts


def send_alert_email(user_email: str, supplier_ruc: str, alerts: list, db: Session) -> bool:
    """Envía email de alerta al usuario cuando detecta cambios."""
    if not alerts:
        return False
    
    email_service = get_email_service()
    
    # Construir mensaje
    alert_descriptions = {
        "score_change": "Cambio en el score de riesgo",
        "osce_new_sanction": "Nueva sanción OSCE detectada",
        "tce_new_sanction": "Nueva sanción TCE detectada"
    }
    
    changes_html = ""
    for alert in alerts:
        desc = alert_descriptions.get(alert["change_type"], alert["change_type"])
        severity_color = {
            "low": "#28a745",
            "medium": "#ffc107",
            "high": "#fd7e14",
            "critical": "#dc3545"
        }.get(alert["severity"], "#6c757d")
        
        changes_html += f"""
        <div style="background: #1a1a1a; border-left: 4px solid {severity_color}; padding: 16px; margin: 12px 0; border-radius: 4px;">
            <div style="color: {severity_color}; font-weight: 600; margin-bottom: 8px;">{desc} ({alert['severity'].upper()})</div>
            <div style="color: #888; font-size: 14px;">Anterior: {alert['previous_status']}</div>
            <div style="color: #f5f5f5; font-size: 14px;">Actual: {alert['new_status']}</div>
        </div>
        """
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Alerta de Conflict Zero</title>
        <style>
            body {{ font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; background: #0a0a0a; margin: 0; padding: 0; color: #f5f5f5; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 40px 20px; }}
            .logo {{ text-align: center; margin-bottom: 30px; }}
            .logo-text {{ font-family: 'Cormorant Garamond', serif; font-size: 28px; color: #c9a961; letter-spacing: 2px; }}
            .card {{ background: #141414; border: 1px solid #2a2a2a; border-radius: 16px; padding: 40px; }}
            h1 {{ font-family: 'Cormorant Garamond', serif; font-size: 24px; font-weight: 500; color: #f5f5f5; margin-bottom: 20px; }}
            p {{ color: #888; line-height: 1.6; margin-bottom: 16px; font-size: 15px; }}
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
                <h1>🔔 Alerta de cambio detectado</h1>
                
                <p>Se han detectado cambios en el proveedor monitoreado:</p>
                <p style="font-size: 18px; color: #f5f5f5; font-weight: 600;">RUC: <span class="highlight">{supplier_ruc}</span></p>
                
                <div style="margin: 24px 0;">
                    {changes_html}
                </div>
                
                <center>
                    <a href="https://czperu.com/dashboard/network.html" class="btn">Ver Mi Red</a>
                </center>
                
                <p style="margin-top: 30px; font-size: 13px; color: #666;">
                    Este es un correo automático de monitoreo. Si deseas modificar la frecuencia de alertas, contacta a soporte.
                </p>
            </div>
            
            <div class="footer">
                <p>© 2026 Conflict Zero. Todos los derechos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return email_service.send_email(
        to_email=user_email,
        subject=f"🚨 Alerta Conflict Zero - Cambio en proveedor {supplier_ruc}",
        html_content=html_content
    )
