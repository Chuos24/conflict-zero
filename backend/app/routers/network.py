"""
Router de Mi Red / Supplier Watchlist

Gestiona proveedores monitoreados y alertas de cambio de estado.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone

from app.core.database import SessionLocal, get_db
from app.core.security import verify_token
from app.models import User, UserSupplier, SupplierAlert, CompanySnapshot
from app.services.snapshot_service import SnapshotService
from app.services.email_service import email_service
from app.services.data_collection import calculate_risk_score, collect_all_data

security = HTTPBearer(auto_error=False)

router = APIRouter(
    prefix="/network",
    tags=["network"],
    responses={401: {"description": "Unauthorized"}},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Obtiene el usuario actual desde el token JWT."""
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Token no proporcionado")
    
    token = credentials.credentials
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    
    return user


# ============================================================================
# Schemas
# ============================================================================

class AddSupplierRequest(BaseModel):
    ruc: str
    supplier_name: Optional[str] = None
    notes: Optional[str] = None


class SupplierResponse(BaseModel):
    id: str
    ruc: str
    supplier_name: str
    risk_level: str
    score: int
    added_at: str
    last_checked: Optional[str] = None
    osce_sanciones: int
    tce_sanciones: int


class AlertResponse(BaseModel):
    id: str
    supplier_ruc: str
    supplier_name: Optional[str] = None
    change_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    severity: str
    is_read: bool
    email_sent: bool
    created_at: str


class NetworkListResponse(BaseModel):
    suppliers: List[SupplierResponse]
    total: int
    alerts_unread: int


class AlertsResponse(BaseModel):
    alerts: List[AlertResponse]
    total: int
    unread_count: int


# ============================================================================
# Helpers
# ============================================================================

async def _fetch_and_cache_supplier_data(db: Session, user_supplier: UserSupplier):
    """
    Consulta datos actualizados del proveedor y actualiza el caché en UserSupplier.
    """
    try:
        # Obtener datos de la empresa (async)
        company_data = await collect_all_data(user_supplier.ruc)
        
        if company_data:
            # Calcular score
            score_data = calculate_risk_score(company_data)
            score = score_data.get("score", 50)
            risk_level = score_data.get("risk_level", "medium")
            
            # Extraer sanciones
            osce_data = company_data.get("osce", {})
            rnp_data = company_data.get("rnp", {})
            osce_sanciones = osce_data.get("sanciones_vigentes", 0)
            tce_sanciones = rnp_data.get("sanciones_vigentes", 0)
            
            # Actualizar caché
            user_supplier.last_score = score
            user_supplier.last_risk_level = risk_level
            user_supplier.last_osce_sanciones = osce_sanciones
            user_supplier.last_tce_sanciones = tce_sanciones
            user_supplier.last_checked_at = datetime.now(timezone.utc)
            
            # Guardar snapshot para ML
            snapshot_service = SnapshotService(db)
            snapshot_service.save_snapshot(
                ruc=user_supplier.ruc,
                sunat_data=company_data.get("sunat"),
                osce_data=osce_data,
                tce_data=rnp_data,
                score_data=score_data,
                source_api="watchlist"
            )
            
            db.commit()
            return True
    except Exception as e:
        print(f"[Network] Error fetching data for {user_supplier.ruc}: {e}")
    
    return False


def _user_supplier_to_response(us: UserSupplier) -> SupplierResponse:
    """Convierte un UserSupplier a SupplierResponse."""
    return SupplierResponse(
        id=us.id,
        ruc=us.ruc,
        supplier_name=us.supplier_name or "Proveedor sin nombre",
        risk_level=us.last_risk_level or "medium",
        score=us.last_score or 50,
        added_at=us.added_at.isoformat() if us.added_at else datetime.now(timezone.utc).isoformat(),
        last_checked=us.last_checked_at.isoformat() if us.last_checked_at else None,
        osce_sanciones=us.last_osce_sanciones or 0,
        tce_sanciones=us.last_tce_sanciones or 0
    )


def _alert_to_response(alert: SupplierAlert) -> AlertResponse:
    """Convierte un SupplierAlert a AlertResponse."""
    return AlertResponse(
        id=alert.id,
        supplier_ruc=alert.supplier_ruc,
        supplier_name=alert.supplier_name,
        change_type=alert.change_type,
        previous_status=alert.previous_status,
        new_status=alert.new_status,
        severity=alert.severity,
        is_read=alert.is_read,
        email_sent=alert.email_sent,
        created_at=alert.created_at.isoformat() if alert.created_at else datetime.now(timezone.utc).isoformat()
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/", response_model=NetworkListResponse)
async def get_network(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de proveedores monitoreados del usuario actual.
    """
    suppliers = db.query(UserSupplier).filter(
        UserSupplier.user_id == user.id
    ).order_by(UserSupplier.added_at.desc()).all()
    
    # Contar alertas sin leer
    alerts_unread = db.query(SupplierAlert).filter(
        SupplierAlert.user_id == user.id,
        SupplierAlert.is_read == False
    ).count()
    
    # Actualizar datos de proveedores si hace más de 24h
    for us in suppliers:
        if not us.last_checked_at or (datetime.now(timezone.utc) - us.last_checked_at).days >= 1:
            await _fetch_and_cache_supplier_data(db, us)
    
    return NetworkListResponse(
        suppliers=[_user_supplier_to_response(s) for s in suppliers],
        total=len(suppliers),
        alerts_unread=alerts_unread
    )


@router.post("/add")
async def add_supplier(
    request: AddSupplierRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Agrega un proveedor a la red de monitoreo del usuario.
    """
    # Validar RUC (11 dígitos)
    ruc_clean = request.ruc.strip()
    if len(ruc_clean) != 11 or not ruc_clean.isdigit():
        raise HTTPException(status_code=400, detail="RUC inválido. Debe tener 11 dígitos numéricos.")
    
    # Verificar si ya existe
    existing = db.query(UserSupplier).filter(
        UserSupplier.user_id == user.id,
        UserSupplier.ruc == ruc_clean
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Este RUC ya está en tu red de monitoreo")
    
    # Crear registro
    user_supplier = UserSupplier(
        user_id=user.id,
        ruc=ruc_clean,
        supplier_name=request.supplier_name,
        notes=request.notes
    )
    db.add(user_supplier)
    db.commit()
    db.refresh(user_supplier)
    
    # Fetch datos iniciales
    await _fetch_and_cache_supplier_data(db, user_supplier)
    
    return {
        "success": True,
        "message": "Proveedor agregado a Mi Red",
        "supplier": _user_supplier_to_response(user_supplier)
    }


@router.delete("/{ruc}")
def remove_supplier(
    ruc: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Elimina un proveedor de la red de monitoreo del usuario.
    """
    supplier = db.query(UserSupplier).filter(
        UserSupplier.user_id == user.id,
        UserSupplier.ruc == ruc
    ).first()
    
    if not supplier:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado en tu red")
    
    db.delete(supplier)
    db.commit()
    
    return {
        "success": True,
        "message": f"Proveedor {ruc} eliminado de Mi Red"
    }


@router.get("/alerts", response_model=AlertsResponse)
def get_alerts(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtiene las alertas del usuario actual.
    """
    alerts = db.query(SupplierAlert).filter(
        SupplierAlert.user_id == user.id
    ).order_by(SupplierAlert.created_at.desc()).all()
    
    unread_count = db.query(SupplierAlert).filter(
        SupplierAlert.user_id == user.id,
        SupplierAlert.is_read == False
    ).count()
    
    return AlertsResponse(
        alerts=[_alert_to_response(a) for a in alerts],
        total=len(alerts),
        unread_count=unread_count
    )


@router.patch("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marca una alerta como leída.
    """
    alert = db.query(SupplierAlert).filter(
        SupplierAlert.id == alert_id,
        SupplierAlert.user_id == user.id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    
    alert.is_read = True
    db.commit()
    
    return {
        "success": True,
        "message": "Alerta marcada como leída"
    }


# ============================================================================
# Funciones para el cron job de re-verificación diaria
# ============================================================================

def check_supplier_changes(db: Session, ruc: str) -> list:
    """
    Verifica cambios en un proveedor comparando el snapshot más reciente
    con el anterior. Retorna lista de alertas si hay cambios.
    
    Esta función es usada por el cron job diario.
    """
    snapshot_service = SnapshotService(db)
    
    # Obtener el snapshot más reciente
    latest = db.query(CompanySnapshot).filter(
        CompanySnapshot.ruc == ruc
    ).order_by(CompanySnapshot.snapshot_date.desc()).first()
    
    if not latest:
        return []
    
    # Detectar cambios usando el servicio existente
    changes = snapshot_service.detect_changes(ruc, latest)
    
    # Convertir a formato de alerta
    alerts = []
    for change in changes:
        alerts.append({
            "change_type": change["type"],
            "previous_status": change.get("previous", ""),
            "new_status": change.get("current", ""),
            "severity": change["severity"]
        })
    
    return alerts


def send_alert_email(to_email: str, ruc: str, alerts: list, db: Session) -> bool:
    """
    Envía email de alerta a un usuario sobre cambios en un proveedor.
    
    Esta función es usada por el cron job diario.
    """
    if not alerts:
        return False
    
    try:
        # Obtener nombre del proveedor del último snapshot
        latest = db.query(CompanySnapshot).filter(
            CompanySnapshot.ruc == ruc
        ).order_by(CompanySnapshot.snapshot_date.desc()).first()
        
        supplier_name = latest.supplier_name if latest else ruc
        
        # Enviar email usando el servicio
        email_service.send_supplier_alert_email(
            to_email=to_email,
            company_name="Empresa",
            supplier_ruc=ruc,
            supplier_name=supplier_name,
            change_type=alerts[0]["change_type"],
            previous_status=alerts[0].get("previous_status", ""),
            new_status=alerts[0].get("new_status", ""),
            severity=alerts[0]["severity"]
        )
        return True
    except Exception as e:
        print(f"[Network] Error sending alert email to {to_email}: {e}")
        return False
