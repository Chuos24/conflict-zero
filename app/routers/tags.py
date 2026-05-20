"""
Tags Router - Conflict Zero
Etiquetado y categorización de verificaciones (Professional+).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User

router = APIRouter(prefix="/tags", tags=["Tags"])

PROFESSIONAL_PLANS = ["professional", "enterprise"]


def _require_professional(user: User):
    if user.plan_type not in PROFESSIONAL_PLANS and not user.is_admin:
        raise HTTPException(status_code=403, detail="Esta función requiere plan Professional o superior.")


_tags_store: dict = {}
_verification_tags: dict = {}


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: Optional[str] = Field(default="#C5A059", pattern=r^"^#[0-9A-Fa-f]{6}$")
    description: Optional[str] = Field(default=None, max_length=200)


class TagResponse(BaseModel):
    id: str
    name: str
    color: str
    description: Optional[str]
    created_at: str
    usage_count: int = 0


class AssignTagRequest(BaseModel):
    tag_id: str
    verification_id: str


@router.post("/", response_model=TagResponse)
async def create_tag(data: TagCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    if uid not in _tags_store:
        _tags_store[uid] = {}
    for t in _tags_store[uid].values():
        if t["name"].lower() == data.name.lower():
            raise HTTPException(status_code=400, detail=f"Ya existe un tag con el nombre '{data.name}'")
    tag_id = str(uuid.uuid4())
    tag = {"id": tag_id, "name": data.name, "color": data.color or "#C5A059", "description": data.description, "created_at": datetime.utcnow().isoformat(), "user_id": uid}
    _tags_store[uid][tag_id] = tag
    return TagResponse(**tag, usage_count=0)


@router.get("/", response_model=List[TagResponse])
async def list_tags(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    tags = list((_tags_store.get(uid) or {}).values())
    ver_tags = _verification_tags.get(uid, {})
    counts: dict = {}
    for tag_ids in ver_tags.values():
        for tid in tag_ids:
            counts[tid] = counts.get(tid, 0) + 1
    return [TagResponse(**t, usage_count=counts.get(t["id"], 0)) for t in tags]


@router.delete("/{tag_id}")
async def delete_tag(tag_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    if uid not in _tags_store or tag_id not in _tags_store[uid]:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    del _tags_store[uid][tag_id]
    for ver_id in (_verification_tags.get(uid) or {}):
        _verification_tags[uid][ver_id] = [t for t in _verification_tags[uid][ver_id] if t != tag_id]
    return {"success": True, "message": "Tag eliminado"}


@router.post("/assign")
async def assign_tag(data: AssignTagRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    if uid not in _tags_store or data.tag_id not in _tags_store[uid]:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    if uid not in _verification_tags:
        _verification_tags[uid] = {}
    if data.verification_id not in _verification_tags[uid]:
        _verification_tags[uid][data.verification_id] = []
    if data.tag_id not in _verification_tags[uid][data.verification_id]:
        _verification_tags[uid][data.verification_id].append(data.tag_id)
    return {"success": True, "message": "Tag asignado", "verification_id": data.verification_id, "tag_id": data.tag_id}


@router.delete("/assign/{verification_id}/{tag_id}")
async def remove_tag_from_verification(verification_id: str, tag_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    if uid in _verification_tags and verification_id in _verification_tags[uid]:
        _verification_tags[uid][verification_id] = [t for t in _verification_tags[uid][verification_id] if t != tag_id]
    return {"success": True, "message": "Tag removido"}


@router.get("/verification/{verification_id}")
async def get_tags_for_verification(verification_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    tag_ids = (_verification_tags.get(uid) or {}).get(verification_id, [])
    user_tags = _tags_store.get(uid, {})
    tags = [TagResponse(**user_tags[tid], usage_count=0) for tid in tag_ids if tid in user_tags]
    return {"verification_id": verification_id, "tags": tags}


@router.get("/search")
async def search_by_tag(tag_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    if uid not in _tags_store or tag_id not in _tags_store[uid]:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    ver_tags = _verification_tags.get(uid, {})
    verification_ids = [vid for vid, tids in ver_tags.items() if tag_id in tids]
    from app.models import VerificationRequest as VR
    results = []
    if verification_ids and db:
        verifications = db.query(VR).filter(VR.id.in_(verification_ids), VR.user_id == uid).all()
        results = [{"id": v.id, "ruc": v.ruc, "company_name": v.company_name, "score": v.score, "risk_level": v.risk_level, "created_at": v.created_at.isoformat() if v.created_at else None} for v in verifications]
    return {"tag": _tags_store[uid][tag_id], "verification_count": len(verification_ids), "verifications": results}
