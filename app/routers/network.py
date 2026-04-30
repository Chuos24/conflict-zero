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

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, NetworkWatchlist, NetworkAlert
from app.services.verification import verification_service

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
    ruc: str
    alias: str


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

    if len(body.ruc) != 11 or not body.ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos numéricos.")

    existing = (
        db.query(NetworkWatchlist)
        .filter(
            NetworkWatchlist.user_id == current_user.id,
            NetworkWatchlist.ruc == body.ruc,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Este RUC ya está en tu watchlist.")

    entry = NetworkWatchlist(
        user_id=current_user.id,
        ruc=body.ruc,
        alias=body.alias,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "success": True,
        "message": f"'{body.alias}' ({body.ruc}) agregado a tu red.",
        "id": entry.id,
    }


@router.get("/", response_model=List[WatchlistEntry])
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
    return entries


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


@router.delete("/remove/{ruc}", status_code=status.HTTP_200_OK)
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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Re-verifica todos los RUCs de todas las watchlists y genera alertas
    cuando hay cambios de estado o score. Solo accesible para admins (cron job).
    """
    _require_admin(current_user)

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
