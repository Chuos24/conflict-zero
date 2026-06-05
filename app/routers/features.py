"""
Features Router - Conflict Zero
Implementa: Search History, Tags/Categorizacion, Templates para Licitaciones.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid
import json

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models import User, VerificationRequest

router = APIRouter(tags=["Features"])


# -
# HELPER: Verificar plan Professional+
# -

def _require_professional(user: User):
    """Requiere plan Professional o Enterprise."""
    professional_plans = {"professional", "enterprise", "admin"}
    plan = (user.plan or "").lower()
    if plan not in professional_plans:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "PLAH_REQUIRED",
                "message": "Esta funcion requiere el plan Professional o superior.",
                "required_plan": "professional",
                "current_plan": plan
            }
        )


# -
# 1. SEARCH HISTORY - todos los planes
# -

@router.get("/history/search", summary="Buscar en historial de verificaciones")
async def search_history(
    q: Optional[str] = Query(None, description="RUC o nombre de empresa"),
    risk_level: Optional[str] = Query(None, description="low|medium|high|critical"),
    score_min: Optional[int] = Query(None, ge=0, le=100),
    score_max: Optional[int] = Query(None, ge=0, le=100),
    date_from: Optional[str] = Query(None, description="Fecha inicio YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="Fecha fin YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Busca en el historial de verificaciones del usuario.
    Soporta filtros por RUC, empresa, nivel de riesgo, score y fechas.
    """
    VR = VerificationRequest

    query = db.query(VR).filter(VR.user_id == current_user.id)

    if q and q.strip():
        q = q.strip()
        query = query.filter(
            or_(
                VR.ruc.ilike(f"%{q}%"),
                VR.company_name.ilike(f"%{q}%")
            )
        )

    if risk_level:
        query = query.filter(VR.risk_level == risk_level)

    if score_min is not None:
        query = query.filter(VR.score >= score_min)
    if score_max is not None:
        query = query.filter(VR.score <= score_max)

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(VR.created_at >= dt_from)
        except ValueError:
            raise HTTPException(status_code=400, detail="date_from debe ser YYYY-MM-DD")

    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d")
            dt_to = dt_to.replace(hour=23, minute=59, second=59)
            query = query.filter(VR.created_at <= dt_to)
        except ValueError:
            raise HTTPException(status_code=400, detail="date_to debe ser YYYY-MM-DD")

    total = query.count()
    results = query.order_by(VR.created_at.desc()).offset(offset).limit(limit).all()

    return {
        "success": True,
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": [
            {
                "id": str(r.id),
                "ruc": r.ruc,
                "company_name": r.company_name,
                "score": r.score,
                "risk_level": r.risk_level,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ]
    }


@router.get("/history/stats", summary="Estadisticas del historial")
async def history_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    VR = VerificationRequest
    records = db.query(VR).filter(VR.user_id == current_user.id).all()
    if not records:
        return {"success": True, "total": 0, "stats": {}}
    scores = [r.score for r in records if r.score is not None]
    by_risk = {}
    for r in records:
        by_risk[r.risk_level] = by_risk.get(r.risk_level, 0) + 1
    return {
        "success": True,
        "total": len(records),
        "stats": {
            "avg_score": round(sum(scores) / len(scores), 1) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "max_score": max(scores) if scores else 0,
            "by_risk_level": by_risk,
            "most_recent": records[0].created_at.isoformat() if records else None,
        }
    }


# -
# 3. TEMPLATES PARA LICITACIONES - Professional+
# -

SYSTEM_TEMPLATES = [
    {"id": "tpl_obras_publicas", "name": "Obras Publicas - Estandar", "description": "Template para procesos de seleccion de obras publicas. Incluye criterios OSCE y score minimo recomendado.", "category": "obras", "type": "system", "criteria": {"score_minimo": 70, "risk_levels_permitidos": ["low", "medium"], "max_sanciones_osce": 0, "max_sanciones_tce": 1, "estado_sunat_requerido": "ACTIVO", "condicion_sunat_requerida": "HABIDO"}, "fields": [{"key": "objeto_licitacion", "label": "Objeto de la Licitacion", "type": "text", "required": True}, {"key": "valor_referencial", "label": "Valor Referencial (S/)", "type": "number", "required": True}, {"key": "plazo_ejecucion", "label": "Plazo de Ejecucion (dias)", "type": "number", "required": True}, {"key": "entidad_convocante", "label": "Entidad Convocante", "type": "text", "required": True}, {"key": "numero_expediente", "label": "Nu Expediente", "type": "text", "required": False}], "created_at": "2026-01-01T00:00:00"},
    {"id": "tpl_bienes_servicios", "name": "Bienes y Servicios - General", "description": "Template estandar para adquisicion de bienes y servicios. Criterios flexibles para proveedores.", "category": "bienes", "type": "system", "criteria": {"score_minimo": 60, "risk_levels_permitidos": ["low", "medium", "high"], "max_sanciones_osce": 2, "max_sanciones_tce": 2, "estado_sunat_requerido": "ACTIVO", "condicion_sunat_requerida": None}, "fields": [{"key": "descripcion_bien", "label": "Descripcion del Bien/Servicio", "type": "text", "required": True}, {"key": "cantidad", "label": "Cantidad", "type": "number", "required": True}, {"key": "precio_unitario", "label": "Precio Unitario Referencial (S/)", "type": "number", "required": True}, {"key": "entidad_convocante", "label": "Entidad Convocante", "type": "text", "required": True}, {"key": "lugar_entrega", "label": "Lugar de Entrega", "type": "text", "required": False}], "created_at": "2026-01-01T00:00:00"},
    {"id": "tpl_consultoria", "name": "Consultoria - Alta Integridad", "description": "Template estricto para servicios de consultoria. Score minimo alto y ceros tolerancia a sanciones.", "category": "consultoria", "type": "system", "criteria": {"score_minimo": 80, "risk_levels_permitidos": ["low"], "max_sanciones_osce": 0, "max_sanciones_tce": 0, "estado_sunat_requerido": "ACTIVO", "condicion_sunat_requerida": "HABIDO"}, "fields": [{"key": "tipo_consultoria", "label": "Tipo de Consultoria", "type": "text", "required": True}, {"key": "alcance", "label": "Alcance del Servicio", "type": "textarea", "required": True}, {"key": "monto_contrato", "label": "Monto del Contrato (S/)", "type": "number", "required": True}, {"key": "entidad_convocante", "label": "Entidad Convocante", "type": "text", "required": True}], "created_at": "2026-01-01T00:00:00"},
    {"id": "tpl_due_diligence", "name": "Due Diligence - Inversion Privada", "description": "Template para evaluacion de socios comerciales e inversiones. Enfoque en ML score y red de conexiones.", "category": "privado", "type": "system", "criteria": {"score_minimo": 75, "risk_levels_permitidos": ["low", "medium"], "max_sanciones_osce": 0, "max_sanciones_tce": 0, "estado_sunat_requerido": "ACTIVO", "condicion_sunat_requerida": "HABIDO"}, "fields": [{"key": "nombre_proyecto", "label": "Nombre del Proyecto / Inversion", "type": "text", "required": True}, {"key": "monto_inversion", "label": "Monto de Inversion (USD)", "type": "number", "required": True}, {"key": "rol_empresa", "label": "Rol de la Empresa Evaluada", "type": "text", "required": True}], "created_at": "2026-01-01T00:00:00"}
]

_user_templates: Dict[str, List[Dict]] = {}


class CreateTemplateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field(..., min_length=2, max_length=50)
    criteria: Dict[str, Any] = Field(default_factory=dict)
    fields: List[Dict[str, Any]] = Field(default_factory=list)


class ApplyTemplateRequest(BaseModel):
    template_id: str
    ruc: str = Field(..., min_length=11, max_length=11)
    field_values: Dict[str, Any] = Field(default_factory=dict)


@router.get("/templates", summary="Listar templates de licitacion")
async def list_templates(
    category: Optional[str] = Query(None),
    type: Optional[str] = Query(None, description="system|custom|all"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    _require_professional(current_user)
    all_templates = []
    if type in (None, "system", "all"):
        system = [t for t in SYSTEM_TEMPLATES if not category or t["category"] == category]
        all_templates.extend(system)
    if type in (None, "custom", "all"):
        user_tpls = [t for t in _user_templates.get(str(current_user.id), []) if not category or t["category"] == category]
        all_templates.extend(user_tpls)
    return {"success": True, "total": len(all_templates), "templates": all_templates}


@router.get("/templates/{template_id}", summary="Obtener template por ID")
async def get_template(template_id: str, current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)):
    _require_professional(current_user)
    for t in SYSTEM_TEMPLATES:
        if t["id"] == template_id:
            return {"success": True, "template": t}
    for t in _user_templates.get(str(current_user.id), []):
        if t["id"] == template_id:
            return {"success": True, "template": t}
    raise HTTPException(status_code=404, detail="Template no encontrado")


@router.post("/templates", summary="Crear template personalizado")
async def create_template(request: CreateTemplateRequest, current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = str(current_user.id)
    if uid not in _user_templates:
        _user_templates[uid] = []
    if len(_user_templates[uid]) >= 20:
        raise HTTPException(status_code=400, detail="Maximo 20 templates personalizados por usuario")
    template = {"id": f"tpl_custom_{uuid.uuid4().hex[8:]}", "name": request.name, "description": request.description, "category": request.category, "type": "custom", "criteria": request.criteria, "fields": request.fields, "created_by": uid, "created_at": datetime.utcnow().isoformat()}
    _user_templates[uid].append(template)
    return {"success": True, "template": template, "message": f"Template '{request.name}' creado exitosamente"}


@router.post("/templates/apply", summary="Aplicar template a un RUC")
async def apply_template(request: ApplyTemplateRequest, current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)):
    _require_professional(current_user)
    template = None
    for t in SYSTEM_TEMPLATES:
        if t["id"] == request.template_id:
            template = t; break
    if not template:
        for t in _user_templates.get(str(current_user.id), []):
            if t["id"] == request.template_id:
                template = t; break
    if not template:
        raise HTTPException(status_code=404, detail="Template no encontrado")
    VR = VerificationRequest
    last_verification = db.query(VR).filter(VR.user_id == current_user.id, VR.ruc == request.ruc).order_by(VR.created_at.desc()).first()
    if not last_verification:
        raise HTTPException(status_code=404, detail=f"No hay verificaciones previas del RUC {request.ruc}. Verifique el RUC primero.")
    criteria = template.get("criteria", {})
    checks = []
    passed_all = True
    score_min = criteria.get("score_minimo", 0)
    score_ok = last_verification.score >= score_min
    checks.append({"criterion": "Score minimo", "required": f">= {score_min}", "actual": last_verification.score, "passed": score_ok})
    if not score_ok: passed_all = False
    allowed_risks = criteria.get("risk_levels_permitidos", ["low", "medium", "high", "critical"])
    risk_ok = last_verification.risk_level in allowed_risks
    checks.append({"criterion": "Nivel de riesgo permitido", "required": ", ".join(allowed_risks), "actual": last_verification.risk_level, "passed": risk_ok})
    if not risk_ok: passed_all = False
    return {"success": True, "eligible": passed_all, "ruc": request.ruc, "template": {"id": template["id"], "name": template["name"]}, "verification_date": last_verification.created_at.isoformat() if last_verification.created_at else None, "score": last_verification.score, "risk_level": last_verification.risk_level, "criteria_evaluation": checks, "field_values": request.field_values, "summary": (f"- {request.ruc} CUMPLE los requisitos" if passed_all else f"- {request.ruc} NO comple todos los requisitos")}


@router.delete("/templates/{template_id}", summary="Eliminar template personalizado")
async def delete_template(template_id: str, current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)):
    _require_professional(current_user)
    uid = str(current_user.id)
    templates = _user_templates.get(uid, [])
    _user_templates[uid] = [t for t in templates if t["id"] != template_id]
    if len(_user_templates[uid]) == len(templates):
        raise HTTPException(status_code=404, detail="Template no encontrado o no tienes permiso para eliminarlo")
    return {"success": True, "message": f"Template {template_id} eliminado"}
