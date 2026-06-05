"""Tags v1 (compat) Router - Contrato tagMap (companyId -> [tags]) para el frontend.

El frontend (src/lib/tags.ts) usa un mapa companyId -> lista de nombres de tag,
persistido por usuario. Este router implementa ese contrato sobre una tabla
ligera UserTagMap (una fila por usuario con JSON), evitando friccion con el
modelo v3 (Tag/RUCTag entidades) que vive en /api/v3/tags.

Disponible para planes Professional / Enterprise.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, List
from datetime import datetime

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, UserTagMap

router = APIRouter(prefix="/tags", tags=["Tags (compat v1)"])

ALLOWED_PLANS = {"professional", "enterprise"}


def _require_pro(user: User):
    if user.plan_type not in ALLOWED_PLANS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta funcion requiere plan Professional o Enterprise.",
        )


class TagUpsert(BaseModel):
    company_id: str = Field(..., min_length=1, max_length=128)
    tags: List[str] = Field(default_factory=list)


def _get_row(db: Session, user: User) -> UserTagMap:
    row = db.query(UserTagMap).filter(UserTagMap.user_id == user.id).first()
    if not row:
        row = UserTagMap(user_id=user.id, data={})
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


@router.get("", summary="Obtener mapa de tags del usuario (companyId -> tags)")
async def get_tag_map(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> Dict[str, List[str]]:
    _require_pro(user)
    row = _get_row(db, user)
    return row.data or {}


@router.post("", summary="Crear/actualizar tags de una empresa")
async def upsert_tags(
    payload: TagUpsert,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_pro(user)
    row = _get_row(db, user)
    data = dict(row.data or {})
    cleaned = []
    seen = set()
    for t in payload.tags:
        t2 = t.strip()
        if t2 and t2 not in seen:
            seen.add(t2)
            cleaned.append(t2)
    if cleaned:
        data[payload.company_id] = cleaned
    else:
        data.pop(payload.company_id, None)
    row.data = data
    row.updated_at = datetime.utcnow()
    # Forzar deteccion de cambio en columna JSON
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(row, "data")
    db.commit()
    return {"success": True}


@router.delete("/{company_id}", summary="Eliminar todos los tags de una empresa")
async def delete_company_tags(
    company_id: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    _require_pro(user)
    row = _get_row(db, user)
    data = dict(row.data or {})
    data.pop(company_id, None)
    row.data = data
    row.updated_at = datetime.utcnow()
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(row, "data")
    db.commit()
    return {"success": True}
