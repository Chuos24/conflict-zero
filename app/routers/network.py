"""
Mi Red — Watchlist de proveedores (Conflict Zero)
Endpoints para monitorear RUCs de proveedores clave del usuario.
Solo disponible para planes Professional / Enterprise.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import os

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, NetworkWatchlist, NetworkAlert
from app.services.verification import verification_service
import os

router = APIRouter(prefix="/network", tags=["Mi Red"])

ALLOWED_PLANS = {"professional", "enterprise"}


# ─── Helpers ────────────────────────────────────────────────────────────────

def _require_pro(user: User):
    if user.plan_type not in ALLOWED_PLANS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta función requiere plan Professional o Enterprise."
        )


def _require_admin(user: User):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ejecutar este endpoint."
        )


# ─── Schemas ────────────────────────────────────────────────────────────────

class AddToWatchlistRequest(BaseModel):
    ruc: Optional[str] = None
    supplier_ruc: Optional[str] = None
    alias: Optional[str] = None
    supplier_name: Optional[str] = None
    notes: Optional[str] = None
    tags: Optional[list] = None

    def get_ruc(self) -> str:
        return self.ruc or self.supplier_ruc or ""

    def get_alias(self) -> str:
        return self.alias or self.supplier_name or "Sin alias"


class WatchlistEntry(BaseModel):
    id: str
    ruc: str
    alias: str
    last_score: Optional[int]
    last_status: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AlertEntry(BaseModel):
    id: str
    ruc: str
    alert_type: str
    old_status: Optional[str]
    new_status: Optional[str]
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/add", status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: AddToWatchlistRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Agrega un RUC a la watchlist del usuario.
    Solo disponible para planes Professional / Enterprise.
    """
    _require_pro(current_user)

    ruc = body.get_ruc()
    if len(ruc) != 11 or not ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos numéricos.")

    existing = (
        db.query(NetworkWatchlist)
        .filter(
            NetworkWatchlist.user_id == current_user.id,
            NetworkWatchlist.ruc == ruc,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Este RUC ya está en tu watchlist.")

    entry = NetworkWatchlist(
        user_id=current_user.id,
        ruc=ruc,
        alias=body.get_alias(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "success": True,
        "message": f"'{body.get_alias()}' ({ruc}) agregado a tu red.",
        "id": entry.id,
    }


@router.get("/stats")
async def network_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Estadísticas de la red del usuario.
    """
    _require_pro(current_user)

    total = db.query(NetworkWatchlist).filter(
        NetworkWatchlist.user_id == current_user.id
    ).count()

    unread_alerts = db.query(NetworkAlert).filter(
        NetworkAlert.user_id == current_user.id,
        NetworkAlert.read_at == None,  # noqa: E711
    ).count()

    # Límite según plan
    plan_limits = {"essential": 0, "professional": 50, "enterprise": 200}
    limit = plan_limits.get(current_user.plan_type, 0)

    # Riesgo basado en last_score
    entries = db.query(NetworkWatchlist).filter(
        NetworkWatchlist.user_id == current_user.id
    ).all()

    high_risk = sum(1 for e in entries if e.last_score is not None and e.last_score < 40)
    medium_risk = sum(1 for e in entries if e.last_score is not None and 40 <= e.last_score < 60)
    low_risk = sum(1 for e in entries if e.last_score is not None and e.last_score >= 60)

    return {
        "success": True,
        "total_suppliers": total,
        "limit": limit,
        "unread_alerts": unread_alerts,
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
    }


@router.get("/")
async def list_watchlist(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Lista todos los proveedores en la watchlist del usuario,
    con su último score y estado.
    """
    _require_pro(current_user)

    entries = (
        db.query(NetworkWatchlist)
        .filter(NetworkWatchlist.user_id == current_user.id)
        .order_by(NetworkWatchlist.created_at.desc())
        .all()
    )

    # Verificar si hay alertas pendientes por RUC
    unread_alert_rucs = {
        row[0] for row in db.query(NetworkAlert.ruc).filter(
            NetworkAlert.user_id == current_user.id,
            NetworkAlert.read_at == None,  # noqa: E711
        ).all()
    }

    result = []
    for e in entries:
        result.append({
            "id": e.id,
            "supplier_ruc": e.ruc,
            "supplier_name": e.alias,
            "alias": e.alias,
            "notes": None,
            "tags": [],
            "current_score": e.last_score,
            "current_status": None,  # Simplificado — el frontend puede hacer fetch adicional
            "has_pending_alerts": e.ruc in unread_alert_rucs,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        })

    return result


@router.get("/alerts", response_model=List[AlertEntry])
async def list_alerts(
    unread_only: bool = True,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Lista las alertas del usuario.
    Por default solo muestra no leídas (unread_only=true).
    Si unread_only=false, muestra todas.
    """
    _require_pro(current_user)

    query = db.query(NetworkAlert).filter(NetworkAlert.user_id == current_user.id)
    if unread_only:
        query = query.filter(NetworkAlert.read_at == None)  # noqa: E711

    alerts = query.order_by(NetworkAlert.created_at.desc()).all()
    return alerts


@router.patch("/alerts/{alert_id}/read", status_code=status.HTTP_200_OK)
async def mark_alert_read(
    alert_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Marca una alerta específica como leída.
    """
    _require_pro(current_user)

    alert = (
        db.query(NetworkAlert)
        .filter(
            NetworkAlert.id == alert_id,
            NetworkAlert.user_id == current_user.id,
        )
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada.")

    alert.read_at = datetime.utcnow()
    db.commit()
    db.refresh(alert)

    return {
        "success": True,
        "message": "Alerta marcada como leída.",
        "alert_id": alert.id,
        "read_at": alert.read_at.isoformat(),
    }


@router.delete("/{ruc}", status_code=status.HTTP_200_OK)
async def remove_from_watchlist(
    ruc: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Elimina un RUC de la watchlist del usuario.
    """
    _require_pro(current_user)

    entry = (
        db.query(NetworkWatchlist)
        .filter(
            NetworkWatchlist.user_id == current_user.id,
            NetworkWatchlist.ruc == ruc,
        )
        .first()
    )
    if not entry:
        raise HTTPException(status_code=404, detail="RUC no encontrado en tu watchlist.")

    db.delete(entry)
    db.commit()

    return {"success": True, "message": f"RUC {ruc} eliminado de tu red."}


@router.post("/verify-all")
async def verify_all(
    authorization: str = Header(None),
    x_admin_token: str = Header(None, alias="X-Admin-Token"),
    db: Session = Depends(get_db),
):
    """
    Re-verifica todos los RUCs de todas las watchlists y genera alertas
    cuando hay cambios de estado o score. Solo accesible para admins (cron job).
    Acepta autenticación via Bearer JWT o X-Admin-Token.
    """
    # Autenticación: Bearer JWT admin OR X-Admin-Token
    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN")
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN no configurado")

    is_admin = False
    current_user = None

    # Intentar X-Admin-Token primero (cron jobs)
    if x_admin_token and x_admin_token == ADMIN_TOKEN:
        is_admin = True
    # Fallback a Bearer JWT
    elif authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
        from app.core.security import verify_token
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub")
            current_user = db.query(User).filter(User.id == user_id).first()
            if current_user and current_user.is_admin:
                is_admin = True

    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden ejecutar este endpoint."
        )

    # Para cron jobs (X-Admin-Token), necesitamos un user object para verification_service
    if current_user is None:
        current_user = db.query(User).filter(User.is_admin == True).first()
        if current_user is None:
            raise HTTPException(status_code=500, detail="No hay usuario admin disponible para cron job")

    entries = db.query(NetworkWatchlist).all()
    updated = 0
    alerts_created = 0
    errors = []

    for entry in entries:
        try:
            result = verification_service.verify_ruc(
                ruc=entry.ruc,
                user=current_user,
                db=db,
            )
            new_score = result.get("score")
            new_status = result.get("sunat_data", {}).get("estado", None)

            changed = False

            if new_score is not None and new_score != entry.last_score:
                alert = NetworkAlert(
                    user_id=entry.user_id,
                    ruc=entry.ruc,
                    alert_type="score_change",
                    old_status=str(entry.last_score) if entry.last_score is not None else None,
                    new_status=str(new_score),
                )
                db.add(alert)
                alerts_created += 1
                changed = True

            if new_status and new_status != entry.last_status:
                alert = NetworkAlert(
                    user_id=entry.user_id,
                    ruc=entry.ruc,
                    alert_type="status_change",
                    old_status=entry.last_status,
                    new_status=new_status,
                )
                db.add(alert)
                alerts_created += 1
                changed = True

            if changed or entry.last_score is None:
                entry.last_score = new_score
                entry.last_status = new_status
                updated += 1

        except Exception as exc:
            errors.append({"ruc": entry.ruc, "error": str(exc)})

    db.commit()

    return {
        "success": True,
        "total_entries": len(entries),
        "updated": updated,
        "alerts_created": alerts_created,
        "errors": errors,
    }
