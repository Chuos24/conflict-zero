"""
Templates Router - Conflict Zero
Templates para licitaciones y bidding (Professional+).	
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User

router = APIRouter(prefix="/templates", tags=["Templates"])

PROFESSIONAL_PLANS = ["professional", "enterprise"]
_templates_store: dict = {}

SYSTEM_TEMPLATES = [
    {"id": "sys-001", "name": "Verificación para Licitación Pública", "description": "Reporte estándar para procesos de selección OSCE. Incluye score, sanciones y estado SUNAT.", "category": "licitacion", "is_system": True, "fields": ["ruc", "company_name", "score", "risk_level", "sunat_status", "osce_sanctions", "tce_sanctions", "verification_date"], "format": "pdf", "custom_notes": None, "created_at": "2026-01-01T00:00:00"},
    {"id": "sys-002", "name": "Due Diligence Proveedor", "description": "Análisis completo para evaluación de proveedores. Incluye ML analysis y score breakdown.", "category": "due_diligence", "is_system": True, "fields": ["ruc", "company_name", "score", "risk_level", "sunat_data", "osce_sanctions", "tce_sanctions", "ml_analysis", "score_breakdown"], "format": "pdf", "custom_notes": None, "created_at": "2026-01-01T00:00:00"},
    {"id": "sys-003", "name": "Reporte Ejecutivo", "description": "Resumen ejecutivo conciso. Solo datos críticos: score, riesgo y alertas principales.", "category": "ejecutivo", "is_system": True, "fields": ["ruc", "company_name", "score", "risk_level", "osce_sanctions_count", "tce_sanctions_count"], "format": "pdf", "custom_notes": None, "created_at": "2026-01-01T00:00:00"},
    {"id": "sys-004", "name": "Evaluación Masiva de Proveedores", "description": "Template para comparar múltiples RUCs. Ideal para auditorías de cadena de suministro.", "category": "masivo", "is_system": True, "fields": ["ruc", "company_name", "score", "risk_level", "sunat_status", "osce_sanctions_count"], "format": "csv", "custom_notes": None, "created_at": "2026-01-01T00:00:00"},
]


def _require_professional(user: User):
    if user.plan_type not in PROFESSIONAL_PLANS and not user.is_admin:
        raise HTTPException(status_code=403, detail="Esta función requiere plan Professional o superior.")


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default="custom", max_length=50)
    fields: List[str] = Field(..., min_length=1)
    format: Optional[str] = Field(default="pdf", pattern=r'^(pdf|csv|json)$')
    custom_notes: Optional[str] = Field(default=None, max_length=1000)


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    category: str
    is_system: bool = False
    fields: List[str]
    format: str
    custom_notes: Optional[str] = None
    created_at: str


class GenerateFromTemplateRequest(BaseModel):
    template_id: str
    ruc: str = Field(..., min_length=11, max_length=11)
    company_name: Optional[str] = None
    score: Optional[int] = None
    risk_level: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


@router.get("/", response_model=List[TemplateResponse])
async def list_templates(category: Optional[str] = None, include_system: bool = True, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    results = []
    if include_system:
        results = [TemplateResponse(**t) for t in SYSTEM_TEMPLATES if not category or _.get("category") == category]
    user_templates = list((_templates_store.get(uid) or {}).values())
    for t in user_templates:
        if not category or t.get("category") == category:
            results.append(TemplateResponse(**t))
    return results


@router.post("/", response_model=TemplateResponse)
async def create_template(data: TemplateCreate, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = current_user.id
    if uid not in _templates_store:
        _templates_store[uid] = {}
    template_id = str(uuid.uuid4())
    template = {"id": template_id, "name": data.name, "description": data.description, "category": data.category or "custom", "is_system": False, "fields": data.fields, "format": data.format or "pdf", "custom_notes": data.custom_notes, "created_at": datetime.utcnow().isoformat()}
    _templates_store[uid][template_id] = template
    return TemplateResponse(**template)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    for t in SYSTEM_TEMPLATES:
        if t["id"] == template_id:
            return TemplateResponse(**t)
    uid = current_user.id
    user_t = (_templates_store.get(uid) or {}).get(template_id)
    if not user_t:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    return TemplateResponse(**user_t)


@router.delete("/{template_id}")
async def delete_template(template_id: str, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    for t in SYSTEM_TEMPLATES:
        if t["id"] == template_id:
            raise HTTPException(status_code=403, detail="No se puedeneliminar templates del sistema")
    uid = current_user.id
    if uid not in _templates_store or template_id not in _templates_store[uid]:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    del _templates_store[uid][template_id]
    return {"success": True, "message": "Template eliminado"}


@router.post("/generate")
async def generate_from_template(data: GenerateFromTemplateRequest, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)):
    _require_professional(current_user)
    template = None
    for t in SYSTEM_TEMPLATES:
        if t["id"] == data.template_id:
            template = t
            break
    if not template:
        uid = current_user.id
        template = (_templates_store.get(uid) or {}).get(data.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    field_map = {"ruc": data.ruc, "company_name": data.company_name or "No disponible", "score": data.score, "risk_level": data.risk_level, "verification_date": datetime.utcnow().isoformat(), "template_name": template["name"], "template_category": template["category"]}
    if data.extra_data:
        field_map.update(data.extra_data)
    payload = {field: field_map.get(field) for field in template["fields"]}
    if template["format"] == "pdf" and data.score is not None and data.risk_level:
        return {"success": True, "template": {"id": template["id"], "name": template["name"], "format": template["format"]}, "data": payload, "action": "ready_to_generate", "message": f"Template '{template['name']}' listo. Use /certificates/generate para generar el PDF.", "suggested_payload": {"ruc": data.ruc, "company_name": data.company_name, "score": data.score, "risk_level": data.risk_level, "sunat_status": payload.get("sunat_status"), "osce_sanctions_count": payload.get("osce_sanctions_count", 0), "tce_sanctions_count": payload.get("tce_sanctions_count", 0)}}
    return {"success": True, "template": {"id": template["id"], "name": template["name"], "format": template["format"]}, "data": payload, "action": "completed", "message": f"Reporte generado con template '{template['name']}'"}
