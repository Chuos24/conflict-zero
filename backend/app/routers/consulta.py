from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.core.security import get_current_active_user, verify_token_optional
from app.models import User
from app.services.verification import verification_service

router = APIRouter(tags=["Consulta Completa"])

@router.get(
    "/consulta-completa/{ruc}",
    summary="Consulta Completa de RUC",
    description="Endpoint compatible con el frontend. Consulta SUNAT, OSCE y TCE."
)
async def consulta_completa(
    ruc: str,
    current_user: User = Depends(verify_token_optional),
    db: Session = Depends(get_db)
):
    """
    Endpoint compatible con el frontend Node.js.
    Consulta datos de SUNAT, sanciones OSCE y TCE.
    """
    # Validar RUC
    if len(ruc) != 11 or not ruc.isdigit():
        return {
            "error": True,
            "message": "RUC debe tener 11 dígitos numéricos",
            "ruc": ruc
        }
    
    try:
        # Realizar verificación (sin autenticación obligatoria para compatibilidad)
        result = verification_service.verify_ruc(
            ruc=ruc,
            user=current_user,
            db=db
        )
        
        # Formato compatible con frontend
        sanciones_list = []
        for s in result.get("osce_sanctions", []):
            sanciones_list.append({
                "entidad": "OSCE",
                "tipo": s.get("severity", "SANCION"),
                "descripcion": s.get("description", ""),
                "fecha": s.get("date"),
                "estado": s.get("status", "ACTIVA")
            })
        for s in result.get("tce_sanctions", []):
            sanciones_list.append({
                "entidad": "TCE", 
                "tipo": s.get("type", "INHABILITACION"),
                "descripcion": s.get("description", ""),
                "fecha": s.get("date"),
                "estado": s.get("status", "ACTIVA")
            })
        
        return {
            "ruc": result["ruc"],
            "razon_social": result.get("company_name", "No disponible"),
            "estado": result.get("risk_level", "DESCONOCIDO").upper(),
            "condicion": result["sunat_data"].get("contributor_status", "HABIDO"),
            "estado_sunat": result["sunat_data"].get("tax_status", "ACTIVO"),
            "direccion": result["sunat_data"].get("address", ""),
            "score": result["score"],
            "sunat": {
                "ruc": result["ruc"],
                "razon_social": result.get("company_name", ""),
                "estado": result["sunat_data"].get("tax_status", "ACTIVO"),
                "condicion": result["sunat_data"].get("contributor_status", "HABIDO"),
                "direccion": result["sunat_data"].get("address", "")
            },
            "sanciones": sanciones_list,
            "total_registros": len(sanciones_list),
            "fuentes": {
                "sunat": True,
                "osce": len(result.get("osce_sanctions", [])),
                "tce": len(result.get("tce_sanctions", []))
            }
        }
    
    except Exception as e:
        import traceback
        print(f"Error en consulta_completa: {e}")
        print(traceback.format_exc())
        return {
            "error": True,
            "message": str(e),
            "ruc": ruc
        }

@router.get(
    "/sunat/ruc/{ruc}",
    summary="Consulta SUNAT",
    description="Obtiene datos básicos de SUNAT para un RUC."
)
async def consulta_sunat(ruc: str):
    """Endpoint simple de consulta SUNAT."""
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": "RUC inválido"}
    
    try:
        result = verification_service.verify_ruc(ruc=ruc, user=None, db=None)
        return {
            "ruc": result["ruc"],
            "razon_social": result.get("company_name"),
            "estado": result["sunat_data"].get("tax_status"),
            "condicion": result["sunat_data"].get("contributor_status"),
            "direccion": result["sunat_data"].get("address")
        }
    except Exception as e:
        return {"error": str(e)}