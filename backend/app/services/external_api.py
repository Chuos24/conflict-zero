import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from app.core.config import get_settings
from app.core.cache import cache
from app.services.scraping import scraping_service

settings = get_settings()

class ExternalAPIService:
    """
    Servicio para consultar APIs externas de datos peruanos.
    Fuente primaria: BuscarUC (buscaruc.com)
    """
    
    def __init__(self):
        # BuscarUC API - Fuente primaria
        self.buscaruc_token = os.getenv("PERU_API_KEY") or os.getenv("PERUAPI_TOKEN")
        self.buscaruc_base_url = "https://buscaruc.com/api/v1"
        
        # Verificar si tenemos API configurada
        self.has_real_api = bool(self.buscaruc_token)
    
    def _call_buscaruc_api(self, ruc: str) -> Optional[Dict]:
        """Llama a BuscarUC API para obtener datos reales de SUNAT"""
        token = os.getenv("PERU_API_KEY") or os.getenv("PERUAPI_TOKEN")
        if not token:
            print(f"[ExternalAPI] No token found!")
            return None
        
        try:
            url = f"{self.buscaruc_base_url}/ruc"
            headers = {"Content-Type": "application/json"}
            payload = {"token": token, "ruc": ruc}
            
            print(f"[ExternalAPI] Calling BuscarUC for RUC: {ruc}")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            data = response.json()
            
            if data.get("error"):
                print(f"[ExternalAPI] BuscarUC error: {data.get('message')}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"[ExternalAPI] Error calling BuscarUC: {e}")
            return None

    def get_sunat_data(self, ruc: str) -> Dict[str, Any]:
        """
        Obtiene datos reales de SUNAT para un RUC via BuscarUC API.
        
        Returns:
            Dict con datos reales de SUNAT o error si no hay API configurada
        """
        cache_key = f"sunat:{ruc}"
        
        # Intentar obtener de caché
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return cached
        
        # BuscarUC API como fuente primaria
        result = self._call_buscaruc_api(ruc)
        
        if result:
            response_data = {
                "ruc": ruc,
                "razon_social": result.get("razonSocial", "").strip() or result.get("nombre", "").strip(),
                "nombre_comercial": result.get("nombreComercial", "").strip(),
                "estado_contribuyente": result.get("estado", "ACTIVO"),
                "condicion_domicilio": result.get("condicion", "HABIDO"),
                "direccion": result.get("direccion", "").strip(),
                "departamento": result.get("departamento", ""),
                "provincia": result.get("provincia", ""),
                "distrito": result.get("distrito", ""),
                "ubigeo": result.get("ubigeo", ""),
                "fuente": "buscaruc_sunat",
                "fecha_consulta": datetime.now().isoformat()
            }
            cache.set(cache_key, response_data, expire=3600)
            return response_data
        
        # No se pudo obtener datos reales
        return {
            "error": True,
            "message": "No se pudieron obtener datos del RUC. Verifica el token de BuscarUC.",
            "ruc": ruc
        }
    
    def get_osce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones OSCE para un RUC via scraping.
        """
        # Usar scraping service
        return scraping_service.get_osce_sanctions(ruc)
    
    def get_tce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones TCE para un RUC via scraping.
        """
        # Usar scraping service
        return scraping_service.get_tce_sanctions(ruc)
    
    def get_full_ruc_data(self, ruc: str) -> Dict[str, Any]:
        """Obtiene todos los datos disponibles para un RUC."""
        sunat_data = self.get_sunat_data(ruc)
        
        # Si hay error en SUNAT, propagar el error
        if sunat_data.get("error"):
            return {
                "error": True,
                "message": sunat_data.get("message"),
                "ruc": ruc
            }
        
        osce_sanctions = self.get_osce_sanctions(ruc)
        tce_sanctions = self.get_tce_sanctions(ruc)
        
        # Determinar fuentes de datos usadas
        data_sources = ["SUNAT"]
        if osce_sanctions:
            data_sources.append("OSCE")
        if tce_sanctions:
            data_sources.append("TCE")
        
        return {
            "ruc": ruc,
            "company_name": sunat_data.get("razon_social", ""),
            "sunat": sunat_data,
            "osce_sanctions": osce_sanctions,
            "tce_sanctions": tce_sanctions,
            "consulted_at": datetime.now().isoformat(),
            "data_sources": data_sources,
            "real_data": True
        }

# Función para obtener una instancia fresca
def get_external_api() -> ExternalAPIService:
    """Retorna una nueva instancia de ExternalAPIService."""
    return ExternalAPIService()
