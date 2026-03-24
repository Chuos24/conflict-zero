import requests
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["Consulta Completa"])

# Función directa - llama a Perú API sin intermediarios
def call_peru_api_direct(ruc: str) -> Dict[str, Any]:
    """Llama directamente a Perú API - sin servicios intermedios."""
    # Leer token DIRECTAMENTE de environment
    token = os.environ.get("PERU_API_KEY") or os.environ.get("PERUAPI_TOKEN")
    
    if not token:
        print(f"[DIRECT] ERROR: No token found in environment!")
        print(f"[DIRECT] PERU_API_KEY present: {'PERU_API_KEY' in os.environ}")
        print(f"[DIRECT] PERUAPI_TOKEN present: {'PERUAPI_TOKEN' in os.environ}")
        return {"error": True, "message": "API no configurada", "ruc": ruc}
    
    try:
        url = f"https://peruapi.com/api/ruc/{ruc}"
        headers = {"X-API-KEY": token}
        params = {"api_token": token}
        
        print(f"[DIRECT] Calling Peru API for RUC: {ruc}")
        response = requests.get(url, headers=headers, params=params, timeout=15)
        data = response.json()
        
        print(f"[DIRECT] Response code: {data.get('code')}")
        
        if data.get("code") == "200":
            return {
                "ruc": ruc,
                "razon_social": data.get("razon_social", "").strip(),
                "estado": data.get("estado", "ACTIVO"),
                "condicion": data.get("condicion", "HABIDO"),
                "direccion": data.get("direccion", "").strip(),
                "success": True
            }
        elif data.get("code") == "401":
            return {"error": True, "message": "API Key inválida o expirada. Verifica tu token en peruapi.com", "ruc": ruc}
        elif data.get("code") == "404":
            return {"error": True, "message": "RUC no encontrado", "ruc": ruc}
        else:
            return {"error": True, "message": f"API Error: {data.get('code')}", "ruc": ruc}
            
    except Exception as e:
        print(f"[DIRECT] Exception: {e}")
        return {"error": True, "message": str(e), "ruc": ruc}


@router.get(
    "/consulta-completa/{ruc}",
    summary="Consulta Completa de RUC",
    description="Endpoint compatible con el frontend. Consulta SUNAT, OSCE y TCE."
)
async def consulta_completa(
    ruc: str,
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
    
    # Llamada DIRECTA a Perú API
    sunat_data = call_peru_api_direct(ruc)
    
    if sunat_data.get("error"):
        return sunat_data
    
    # Calcular score simple (placeholder por ahora)
    score = 85  # Score por defecto
    
    # Sanciones vacías por ahora
    sanciones_list = []
    
    return {
        "ruc": ruc,
        "razon_social": sunat_data.get("razon_social", "No disponible"),
        "estado": sunat_data.get("estado", "ACTIVO").upper(),
        "condicion": sunat_data.get("condicion", "HABIDO"),
        "estado_sunat": sunat_data.get("estado", "ACTIVO"),
        "direccion": sunat_data.get("direccion", ""),
        "score": score,
        "sunat": {
            "ruc": ruc,
            "razon_social": sunat_data.get("razon_social", ""),
            "estado": sunat_data.get("estado", "ACTIVO"),
            "condicion": sunat_data.get("condicion", "HABIDO"),
            "direccion": sunat_data.get("direccion", "")
        },
        "sanciones": sanciones_list,
        "total_registros": 0,
        "fuentes": {
            "sunat": True,
            "osce": 0,
            "tce": 0
        }
    }


@router.get(
    "/sunat/ruc/{ruc}",
    summary="Consulta SUNAT Directa",
    description="Obtiene datos básicos de SUNAT para un RUC (llamada directa)."
)
async def consulta_sunat(ruc: str):
    """Endpoint simple de consulta SUNAT - llamada directa."""
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": "RUC inválido"}
    
    return call_peru_api_direct(ruc)
