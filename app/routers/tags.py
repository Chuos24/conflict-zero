"""Tags Router - Categorizacion de RUCs para Professional+"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, Tag, RUCTag

router = APIRouter(prefix="/tags", tags=["Tags & Categorizacion"])


# ============================================================
# SCHEMAS
# ============================================================

class TagCreate(BaseModel):
    """Schema para crear un tag"""
    name: str = Field(..., min_length=1, max_length=50, description="Nombre del tag")
    color: Optional[str] = Field(default="#C5A059", pattern="^#[0-9A-F]{6}$", description="Color hex (ej: #C5A059)")
    description: Optional[str] = Field(None, max_length=500, description="Descripcion del tag")


class TagUpdate(BaseModel):
    """Schema para actualizar un tag"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    color: Optional[str] = Field(None, pattern="^#[0-9A-F]{6}$")
    description: Optional[str] = Field(None, max_length=500)


class TagResponse(BaseModel):
    """Schema de respuesta de tag"""
    id: str
    name: str
    color: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True


class RUCTagCreate(BaseModel):
    """Schema para asignar tag a RUC"""
    ruc: str = Field(..., min_length=11, max_length=11, description="RUC de 11 digitos")
    tag_id: str = Field(..., description="ID del tag")
    notes: Optional[str] = Field(None, max_length=500, description="Notas adicionales")


class RUCTagResponse(BaseModel):
    """Schema de respuesta RUC-Tag"""
    id: str
    ruc: str
    tag_id: str
    tag: TagResponse
    notes: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================
# HELPERS
# ============================================================

def check_plan_professional(user: User):
    """Verifica que el usuario tenga plan Professional o superior"""
    allowed_plans = {"professional", "enterprise"}
    if user.plan_type not in allowed_plans:
        raise HTTPException(
            status_code=403,
            detail="Esta funcion solo esta disponible para planes Professional+"
        )


# ============================================================
# ENDPOINTS - TAGS
# ============================================================

@router.post("", response_model=TagResponse, summary="Crear nuevo tag")
async def create_tag(
    data: TagCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Crea un nuevo tag para categorizar RUCs"""
    check_plan_professional(user)
    
    # Verificar que el nombre sea unico para este usuario
    existing = db.query(Tag).filter(
        and_(Tag.user_id == user.id, Tag.name == data.name)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un tag con el nombre '{data.name}'"
        )
    
    tag = Tag(
        user_id=user.id,
        name=data.name,
        color=data.color or "#C5A059",
        description=data.description
    )
    
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return tag


@router.get("", response_model=List[TagResponse], summary="Listar tags del usuario")
async def list_tags(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    active_only: bool = Query(True, description="Solo tags activos")
):
    """Obtiene todos los tags del usuario autenticado"""
    check_plan_professional(user)
    
    query = db.query(Tag).filter(Tag.user_id == user.id)
    
    if active_only:
        query = query.filter(Tag.is_active == True)
    
    tags = query.order_by(Tag.created_at.desc()).all()
    
    return tags


@router.get("/{tag_id}", response_model=TagResponse, summary="Obtener detalle de tag")
async def get_tag(
    tag_id: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene los detalles de un tag especifico"""
    check_plan_professional(user)
    
    tag = db.query(Tag).filter(
        and_(Tag.id == tag_id, Tag.user_id == user.id)
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    
    return tag


@router.put("/{tag_id}", response_model=TagResponse, summary="Actualizar tag")
async def update_tag(
    tag_id: str,
    data: TagUpdate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Actualiza un tag existente"""
    check_plan_professional(user)
    
    tag = db.query(Tag).filter(
        and_(Tag.id == tag_id, Tag.user_id == user.id)
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    
    # Actualizar campos solo si se proporcionan
    if data.name:
        # Verificar unicidad del nuevo nombre
        existing = db.query(Tag).filter(
            and_(Tag.user_id == user.id, Tag.name == data.name, Tag.id != tag_id)
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe otro tag con ese nombre")
        tag.name = data.name
    
    if data.color:
        tag.color = data.color
    
    if data.description is not None:
        tag.description = data.description
    
    tag.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tag)
    
    return tag


@router.delete("/{tag_id}", summary="Eliminar tag")
async def delete_tag(
    tag_id: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Elimina un tag (soft delete)"""
    check_plan_professional(user)
    
    tag = db.query(Tag).filter(
        and_(Tag.id == tag_id, Tag.user_id == user.id)
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    
    # Soft delete
    tag.is_active = False
    tag.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"ok": True, "message": "Tag eliminado"}


@router.get("/search/{query}", response_model=List[TagResponse], summary="Buscar tags")
async def search_tags(
    query: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Busca tags por nombre (case-insensitive)"""
    check_plan_professional(user)
    
    tags = db.query(Tag).filter(
        and_(
            Tag.user_id == user.id,
            Tag.is_active == True,
            Tag.name.ilike(f"%{query}%")
        )
    ).all()
    
    return tags


# ============================================================
# ENDPOINTS - RUC-TAGS
# ============================================================

@router.post("/{tag_id}/assign", response_model=RUCTagResponse, summary="Asignar tag a RUC")
async def assign_tag_to_ruc(
    tag_id: str,
    data: RUCTagCreate,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Asigna un tag a un RUC"""
    check_plan_professional(user)
    
    # Verificar que el tag existe y pertenece al usuario
    tag = db.query(Tag).filter(
        and_(Tag.id == tag_id, Tag.user_id == user.id)
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    
    # Verificar que no exista ya la asociacion
    existing = db.query(RUCTag).filter(
        and_(
            RUCTag.user_id == user.id,
            RUCTag.tag_id == tag_id,
            RUCTag.ruc == data.ruc
        )
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Este RUC ya tiene asignado este tag")
    
    # Crear asociacion
    ruc_tag = RUCTag(
        user_id=user.id,
        tag_id=tag_id,
        ruc=data.ruc,
        notes=data.notes
    )
    
    db.add(ruc_tag)
    db.commit()
    db.refresh(ruc_tag)
    
    return ruc_tag


@router.get("/{tag_id}/rucs", response_model=List[RUCTagResponse], summary="Listar RUCs de un tag")
async def get_tag_rucs(
    tag_id: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los RUCs asignados a un tag"""
    check_plan_professional(user)
    
    # Verificar que el tag existe y pertenece al usuario
    tag = db.query(Tag).filter(
        and_(Tag.id == tag_id, Tag.user_id == user.id)
    ).first()
    
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    
    ruc_tags = db.query(RUCTag).filter(
        and_(RUCTag.tag_id == tag_id, RUCTag.user_id == user.id)
    ).order_by(RUCTag.created_at.desc()).all()
    
    return ruc_tags


@router.delete("/{tag_id}/rucs/{ruc}", summary="Desasignar tag de RUC")
async def remove_tag_from_ruc(
    tag_id: str,
    ruc: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Desasigna un tag de un RUC"""
    check_plan_professional(user)
    
    ruc_tag = db.query(RUCTag).filter(
        and_(
            RUCTag.user_id == user.id,
            RUCTag.tag_id == tag_id,
            RUCTag.ruc == ruc
        )
    ).first()
    
    if not ruc_tag:
        raise HTTPException(status_code=404, detail="Asociacion no encontrada")
    
    db.delete(ruc_tag)
    db.commit()
    
    return {"ok": True, "message": "Tag desasignado del RUC"}


@router.get("/ruc/{ruc}/tags", response_model=List[TagResponse], summary="Listar tags de un RUC")
async def get_ruc_tags(
    ruc: str,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Obtiene todos los tags asignados a un RUC"""
    check_plan_professional(user)
    
    ruc_tags = db.query(RUCTag).filter(
        and_(RUCTag.ruc == ruc, RUCTag.user_id == user.id)
    ).all()
    
    tags = [rt.tag for rt in ruc_tags]
    
    return tags
