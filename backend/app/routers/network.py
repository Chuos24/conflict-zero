"""
Mi Red - Router para Supplier Watchlist
Feature que permite a usuarios monitorear proveedores y recibir alertas de cambios
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_user
from app.models import (
    User, SupplierAlert, CompanySnapshot, VerificationRequest,
    SupplierWatchlist  # Nuevo modelo que crearé
)
from app.schemas import (
    SupplierWatchlistCreate, SupplierWatchlistResponse,
    SupplierAlertResponse, SupplierAlertUpdate,
    NetworkStatsResponse
)

router = APIRouter(prefix="/network", tags=["network"])


@router.post("/add", response_model=SupplierWatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_supplier_to_network(
    data: SupplierWatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Agregar un RUC a la watchlist del usuario para monitoreo.
    El usuario será notificado si hay cambios en el estado del proveedor.
    """
    # Verificar límite según plan
    plan_limits = {
        "essential": 10,
        "professional": 50,
        "enterprise": 200
    }
    limit = plan_limits.get(current_user.plan_type, 10)
    
    current_count = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.is_active == True
        )
    ).count()
    
    if current_count >= limit:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Límite de {limit} proveedores alcanzado para plan {current_user.plan_type}. "
                   f"Actualiza tu plan para monitorear más proveedores."
        )
    
    # Verificar si ya existe
    existing = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.supplier_ruc == data.supplier_ruc,
            SupplierWatchlist.is_active == True
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El RUC {data.supplier_ruc} ya está en tu red"
        )
    
    # Obtener último snapshot para datos iniciales
    last_snapshot = db.query(CompanySnapshot).filter(
        CompanySnapshot.ruc == data.supplier_ruc
    ).order_by(desc(CompanySnapshot.snapshot_date)).first()
    
    # Crear entrada en watchlist
    watchlist_entry = SupplierWatchlist(
        user_id=current_user.id,
        supplier_ruc=data.supplier_ruc,
        supplier_name=data.supplier_name or (last_snapshot.supplier_name if last_snapshot else None),
        alias=data.alias,
        notes=data.notes,
        tags=data.tags or [],
        is_active=True,
        last_snapshot_id=last_snapshot.id if last_snapshot else None,
        created_at=datetime.utcnow()
    )
    
    db.add(watchlist_entry)
    db.commit()
    db.refresh(watchlist_entry)
    
    return watchlist_entry


@router.get("/", response_model=List[SupplierWatchlistResponse])
async def get_network_list(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Obtener lista de todos los proveedores en la red del usuario con su último estado.
    """
    entries = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.is_active == True
        )
    ).order_by(desc(SupplierWatchlist.created_at)).offset(skip).limit(limit).all()
    
    # Enriquecer con datos del último snapshot
    result = []
    for entry in entries:
        response_data = {
            "id": entry.id,
            "user_id": entry.user_id,
            "supplier_ruc": entry.supplier_ruc,
            "supplier_name": entry.supplier_name,
            "alias": entry.alias,
            "notes": entry.notes,
            "tags": entry.tags,
            "is_active": entry.is_active,
            "created_at": entry.created_at,
            "updated_at": entry.updated_at,
            "last_checked_at": entry.last_checked_at,
            "current_status": None,
            "current_score": None,
            "has_pending_alerts": False
        }
        
        # Obt último snapshot
        last_snapshot = db.query(CompanySnapshot).filter(
            CompanySnapshot.ruc == entry.supplier_ruc
        ).order_by(desc(CompanySnapshot.snapshot_date)).first()
        
        if last_snapshot:
            response_data["current_status"] = {
                "sunat_status": last_snapshot.sunat_status,
                "sunat_debt": last_snapshot.sunat_debt,
                "osce_inhabilitado": last_snapshot.osce_inhabilitado,
                "osce_sanciones_vigentes": last_snapshot.osce_sanciones_vigentes,
                "tce_sanciones_count": last_snapshot.tce_sanciones_count,
                "snapshot_date": last_snapshot.snapshot_date
            }
            response_data["current_score"] = last_snapshot.score_calculado
        
        # Verificar si tiene alertas no leídas
        pending_alerts = db.query(SupplierAlert).filter(
            and_(
                SupplierAlert.user_id == current_user.id,
                SupplierAlert.supplier_ruc == entry.supplier_ruc,
                SupplierAlert.is_read == False
            )
        ).count()
        response_data["has_pending_alerts"] = pending_alerts > 0
        
        result.append(SupplierWatchlistResponse(**response_data))
    
    return result


@router.get("/stats", response_model=NetworkStatsResponse)
async def get_network_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Estadísticas de la red del usuario.
    """
    total_suppliers = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.is_active == True
        )
    ).count()
    
    unread_alerts = db.query(SupplierAlert).filter(
        and_(
            SupplierAlert.user_id == current_user.id,
            SupplierAlert.is_read == False
        )
    ).count()
    
    # Contar por nivel de riesgo basado en últimos snapshots
    high_risk_count = 0
    medium_risk_count = 0
    low_risk_count = 0
    
    entries = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.is_active == True
        )
    ).all()
    
    for entry in entries:
        last_snapshot = db.query(CompanySnapshot).filter(
            CompanySnapshot.ruc == entry.supplier_ruc
        ).order_by(desc(CompanySnapshot.snapshot_date)).first()
        
        if last_snapshot and last_snapshot.score_calculado:
            score = last_snapshot.score_calculado
            if score < 40:
                high_risk_count += 1
            elif score < 70:
                medium_risk_count += 1
            else:
                low_risk_count += 1
    
    # Límite según plan
    plan_limits = {
        "essential": 10,
        "professional": 50,
        "enterprise": 200
    }
    limit = plan_limits.get(current_user.plan_type, 10)
    
    return NetworkStatsResponse(
        total_suppliers=total_suppliers,
        limit=limit,
        unread_alerts=unread_alerts,
        high_risk_count=high_risk_count,
        medium_risk_count=medium_risk_count,
        low_risk_count=low_risk_count
    )


@router.delete("/{ruc}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_supplier_from_network(
    ruc: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Eliminar un RUC de la watchlist del usuario.
    """
    entry = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.supplier_ruc == ruc,
            SupplierWatchlist.is_active == True
        )
    ).first()
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El RUC {ruc} no está en tu red"
        )
    
    entry.is_active = False
    entry.updated_at = datetime.utcnow()
    db.commit()
    
    return None


@router.get("/alerts", response_model=List[SupplierAlertResponse])
async def get_network_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    unread_only: bool = False,
    skip: int = 0,
    limit: int = 50
):
    """
    Obtener alertas de la red del usuario.
    Opcionalmente filtrar solo las no leídas.
    """
    query = db.query(SupplierAlert).filter(
        SupplierAlert.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(SupplierAlert.is_read == False)
    
    alerts = query.order_by(desc(SupplierAlert.created_at)).offset(skip).limit(limit).all()
    
    return alerts


@router.patch("/alerts/{alert_id}/read", response_model=SupplierAlertResponse)
async def mark_alert_as_read(
    alert_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marcar una alerta como leída.
    """
    alert = db.query(SupplierAlert).filter(
        and_(
            SupplierAlert.id == alert_id,
            SupplierAlert.user_id == current_user.id
        )
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alerta no encontrada"
        )
    
    alert.is_read = True
    db.commit()
    db.refresh(alert)
    
    return alert


@router.patch("/alerts/read-all", status_code=status.HTTP_200_OK)
async def mark_all_alerts_as_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Marcar todas las alertas del usuario como leídas.
    """
    db.query(SupplierAlert).filter(
        and_(
            SupplierAlert.user_id == current_user.id,
            SupplierAlert.is_read == False
        )
    ).update({"is_read": True})
    
    db.commit()
    
    return {"message": "Todas las alertas marcadas como leídas"}


@router.get("/supplier/{ruc}/history")
async def get_supplier_history(
    ruc: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = 90
):
    """
    Obtener historial de cambios de un proveedor específico en la red.
    """
    # Verificar que el proveedor está en la red del usuario
    in_network = db.query(SupplierWatchlist).filter(
        and_(
            SupplierWatchlist.user_id == current_user.id,
            SupplierWatchlist.supplier_ruc == ruc,
            SupplierWatchlist.is_active == True
        )
    ).first()
    
    if not in_network:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este RUC no está en tu red de proveedores"
        )
    
    # Obtener snapshots del período
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=days)
    
    snapshots = db.query(CompanySnapshot).filter(
        and_(
            CompanySnapshot.ruc == ruc,
            CompanySnapshot.snapshot_date >= since
        )
    ).order_by(CompanySnapshot.snapshot_date).all()
    
    # Obtener alertas del período
    alerts = db.query(SupplierAlert).filter(
        and_(
            SupplierAlert.user_id == current_user.id,
            SupplierAlert.supplier_ruc == ruc,
            SupplierAlert.created_at >= since
        )
    ).order_by(desc(SupplierAlert.created_at)).all()
    
    return {
        "ruc": ruc,
        "supplier_name": in_network.supplier_name,
        "period_days": days,
        "snapshots_count": len(snapshots),
        "alerts_count": len(alerts),
        "snapshots": [
            {
                "date": s.snapshot_date,
                "score": s.score_calculado,
                "sunat_debt": s.sunat_debt,
                "osce_inhabilitado": s.osce_inhabilitado,
                "osce_sanciones_vigentes": s.osce_sanciones_vigentes
            }
            for s in snapshots
        ],
        "alerts": [
            {
                "id": a.id,
                "change_type": a.change_type,
                "previous_status": a.previous_status,
                "new_status": a.new_status,
                "severity": a.severity,
                "created_at": a.created_at,
                "is_read": a.is_read
            }
            for a in alerts
        ]
    }
