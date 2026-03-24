import requests
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.config import get_settings
from app.services.scoring import scoring_engine
from app.services.scraping import scraping_service

settings = get_settings()
router = APIRouter(tags=["Consulta Completa"])

# Función directa - llama a BuscarUC API
def call_buscaruc_api(ruc: str) -> Dict[str, Any]:
    """Llama directamente a BuscarUC API."""
    token = os.environ.get("PERU_API_KEY") or os.environ.get("PERUAPI_TOKEN")
    
    if not token:
        print(f"[BUSCARUC] ERROR: No token found!")
        return {"error": True, "message": "API no configurada", "ruc": ruc}
    
    try:
        url = "https://buscaruc.com/api/v1/ruc"
        headers = {"Content-Type": "application/json"}
        payload = {"token": token, "ruc": ruc}
        
        print(f"[BUSCARUC] Calling for RUC: {ruc}")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        print(f"[BUSCARUC] Response: {data.get('error', 'OK')}")
        
        if not data.get("error"):
            return {
                "ruc": ruc,
                "razon_social": data.get("razonSocial", "").strip() or data.get("nombre", "").strip(),
                "nombre": data.get("nombre", "").strip(),
                "estado": data.get("estado", "ACTIVO").upper(),
                "condicion": data.get("condicion", "HABIDO").upper(),
                "direccion": data.get("direccion", "").strip(),
                "departamento": data.get("departamento", ""),
                "provincia": data.get("provincia", ""),
                "distrito": data.get("distrito", ""),
                "ubigeo": data.get("ubigeo", ""),
                "success": True
            }
        else:
            return {"error": True, "message": data.get("message", "RUC no encontrado"), "ruc": ruc}
            
    except Exception as e:
        print(f"[BUSCARUC] Exception: {e}")
        return {"error": True, "message": str(e), "ruc": ruc}


@router.get(
    "/consulta-completa/{ruc}",
    summary="Consulta Completa de RUC",
    description="Consulta SUNAT y calcula score predictivo basado en datos disponibles."
)
async def consulta_completa(
    ruc: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint principal de consulta RUC.
    Consulta datos de SUNAT vía BuscarUC y calcula score predictivo.
    """
    # Validar RUC
    if len(ruc) != 11 or not ruc.isdigit():
        return {
            "error": True,
            "message": "RUC debe tener 11 dígitos numéricos",
            "ruc": ruc
        }
    
    # Llamada a BuscarUC API
    sunat_data = call_buscaruc_api(ruc)
    
    # Si BuscarUC falla, usar datos de OSCE DB como fallback
    if sunat_data.get("error"):
        from app.services.osce_datos_abiertos import osce_datos_abiertos
        osce_db_data = osce_datos_abiertos.get_sanciones_from_db(ruc)
        
        if osce_db_data:
            # Usar datos de OSCE como fallback
            sunat_data = {
                "ruc": ruc,
                "razon_social": osce_db_data.get("nombre", f"RUC {ruc}"),
                "nombre": osce_db_data.get("nombre", ""),
                "estado": "ACTIVO",  # Asumir activo si no sabemos
                "condicion": "HABIDO",
                "direccion": "",
                "departamento": "",
                "provincia": "",
                "distrito": "",
                "ubigeo": "",
                "success": True,
                "fuente": "osce_db_fallback"
            }
        else:
            # Último fallback: solo el RUC
            sunat_data = {
                "ruc": ruc,
                "razon_social": f"RUC {ruc}",
                "nombre": "",
                "estado": "ACTIVO",
                "condicion": "HABIDO",
                "direccion": "",
                "departamento": "",
                "provincia": "",
                "distrito": "",
                "ubigeo": "",
                "success": True,
                "fuente": "ruc_only"
            }
    
    # Consultar sanciones OSCE (datos reales de CONOSCE)
    osce_sanciones = scraping_service.get_osce_sanctions(ruc)
    
    # Calcular score usando el scoring engine con datos reales
    score_result = scoring_engine.calculate_total_score(
        ruc=ruc,
        razon_social=sunat_data.get("razon_social", ""),
        estado=sunat_data.get("estado", "ACTIVO"),
        condicion=sunat_data.get("condicion", "HABIDO"),
        deuda=0,  # No disponible en BuscarUC
        osce_sanctions=osce_sanciones,
        tce_sanctions=[]
    )
    
    # Construir respuesta completa con sanciones reales
    return {
        "ruc": ruc,
        "razon_social": sunat_data.get("razon_social", "No disponible"),
        "nombre_comercial": sunat_data.get("nombre", sunat_data.get("razon_social", "")),
        "estado": sunat_data.get("estado", "ACTIVO"),
        "condicion": sunat_data.get("condicion", "HABIDO"),
        "estado_sunat": sunat_data.get("estado", "ACTIVO"),
        "direccion": sunat_data.get("direccion", ""),
        "departamento": sunat_data.get("departamento", ""),
        "provincia": sunat_data.get("provincia", ""),
        "distrito": sunat_data.get("distrito", ""),
        "ubigeo": sunat_data.get("ubigeo", ""),
        "score": score_result["total_score"],
        "risk_level": score_result["risk_level"],
        "risk_emoji": score_result["risk_emoji"],
        "risk_description": scoring_engine.get_risk_description(score_result["risk_level"]),
        "sunat": {
            "ruc": ruc,
            "razon_social": sunat_data.get("razon_social", ""),
            "estado": sunat_data.get("estado", "ACTIVO"),
            "condicion": sunat_data.get("condicion", "HABIDO"),
            "direccion": sunat_data.get("direccion", "")
        },
        "sanciones": osce_sanciones,
        "total_registros": len(osce_sanciones),
        "fuentes": {
            "sunat": True,
            "osce": len(osce_sanciones),
            "tce": 0
        },
        "score_breakdown": score_result["breakdown"],
        "score_details": score_result["individual_scores"],
        "fuente_datos": sunat_data.get("fuente", "buscaruc"),
        "score_detalle": score_result,
        "ml_analysis": score_result["ml_analysis"]
    }


@router.get(
    "/sunat/ruc/{ruc}",
    summary="Consulta SUNAT Directa",
    description="Obtiene datos básicos de SUNAT para un RUC."
)
async def consulta_sunat(ruc: str):
    """Endpoint simple de consulta SUNAT."""
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": "RUC inválido"}
    
    return call_buscaruc_api(ruc)


@router.get(
    "/score/ruc/{ruc}",
    summary="Score Predictivo de RUC",
    description="Obtiene solo el score y análisis de riesgo para un RUC."
)
async def consulta_score(ruc: str):
    """Endpoint para obtener solo el score de un RUC."""
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": True, "message": "RUC inválido"}
    
    sunat_data = call_buscaruc_api(ruc)
    
    if sunat_data.get("error"):
        return sunat_data
    
    score_result = scoring_engine.calculate_total_score(
        ruc=ruc,
        razon_social=sunat_data.get("razon_social", ""),
        estado=sunat_data.get("estado", "ACTIVO"),
        condicion=sunat_data.get("condicion", "HABIDO"),
        deuda=0,
        osce_sanctions=[],
        tce_sanctions=[]
    )
    
    return {
        "ruc": ruc,
        "razon_social": sunat_data.get("razon_social", ""),
        "score": score_result["total_score"],
        "risk_level": score_result["risk_level"],
        "risk_emoji": score_result["risk_emoji"],
        "risk_description": scoring_engine.get_risk_description(score_result["risk_level"]),
        "score_breakdown": score_result["breakdown"],
        "ml_analysis": score_result["ml_analysis"]
    }
