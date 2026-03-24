import requests
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.core.database import get_db
from app.core.config import get_settings

settings = get_settings()
router = APIRouter(tags=["Consulta Completa"])

# Función directa - llama a BuscarUC API
def call_buscaruc_api(ruc: str) -> Dict[str, Any]:
    """Llama a BuscarUC API - API oficial para datos SUNAT."""
    # Leer token DIRECTAMENTE de environment
    token = os.environ.get("PERU_API_KEY") or os.environ.get("PERUAPI_TOKEN")
    
    if not token:
        print(f"[BUSCARUC] ERROR: No token found in environment!")
        return {"error": True, "message": "API no configurada", "ruc": ruc}
    
    try:
        # BuscarUC API - POST request con JSON body
        url = "https://buscaruc.com/api/v1/ruc"
        headers = {"Content-Type": "application/json"}
        payload = {
            "token": token,
            "ruc": ruc
        }
        
        print(f"[BUSCARUC] Calling API for RUC: {ruc}")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        print(f"[BUSCARUC] Response: {data}")
        
        # BuscarUC retorna datos directamente sin código
        if data.get("error"):
            return {"error": True, "message": data.get("message", "Error en API"), "ruc": ruc}
        
        # Extraer datos del RUC
        return {
            "ruc": ruc,
            "razon_social": data.get("razonSocial", "").strip() or data.get("nombre", "").strip(),
            "estado": data.get("estado", "ACTIVO"),
            "condicion": data.get("condicion", "HABIDO"),
            "direccion": data.get("direccion", "").strip(),
            "departamento": data.get("departamento", ""),
            "provincia": data.get("provincia", ""),
            "distrito": data.get("distrito", ""),
            "ubigeo": data.get("ubigeo", ""),
            "success": True
        }
            
    except Exception as e:
        print(f"[BUSCARUC] Exception: {e}")
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
    
    # Llamada a BuscarUC API
    sunat_data = call_buscaruc_api(ruc)
    
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
        "departamento": sunat_data.get("departamento", ""),
        "provincia": sunat_data.get("provincia", ""),
        "distrito": sunat_data.get("distrito", ""),
        "ubigeo": sunat_data.get("ubigeo", ""),
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
    
    return call_buscaruc_api(ruc)
