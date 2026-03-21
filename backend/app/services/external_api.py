import requests
from typing import Dict, List, Any, Optional
from datetime import datetime
from app.core.config import get_settings
from app.core.cache import cache

settings = get_settings()

class ExternalAPIService:
    """
    Servicio para consultar APIs externas de datos peruanos.
    Fuente primaria: Perú API (peruapi.com)
    """
    
    def __init__(self):
        # Perú API - Fuente primaria
        self.peruapi_token = settings.PERUAPI_TOKEN
        self.peruapi_base_url = "https://peruapi.com"
        
        # Verificar si tenemos API configurada
        self.has_real_api = bool(self.peruapi_token)
    
    def _call_peru_api(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Llama a Perú API para obtener datos reales de SUNAT"""
        if not self.peruapi_token:
            return None
        
        try:
            url = f"{self.peruapi_base_url}/{endpoint}"
            headers = {
                "X-API-KEY": self.peruapi_token,
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            # Añadir api_token a params si no está
            if params is None:
                params = {}
            if "api_token" not in params:
                params["api_token"] = self.peruapi_token
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error llamando Perú API: {e}")
            return None

    def get_sunat_data(self, ruc: str) -> Dict[str, Any]:
        """
        Obtiene datos reales de SUNAT para un RUC via Perú API.
        
        Returns:
            Dict con datos reales de SUNAT o error si no hay API configurada
        """
        cache_key = f"sunat:{ruc}"
        
        # Intentar obtener de caché
        cached = cache.get(cache_key)
        if cached:
            cached["cached"] = True
            return cached
        
        # Perú API como fuente primaria
        if self.peruapi_token:
            result = self._call_peru_api(f"api/ruc/{ruc}")
            
            if result and result.get("code") == "200":
                response_data = {
                    "ruc": ruc,
                    "razon_social": result.get("razon_social", "").strip(),
                    "nombre_comercial": result.get("razon_social", "").strip(),
                    "estado_contribuyente": result.get("estado", "ACTIVO"),
                    "condicion_domicilio": result.get("condicion", "HABIDO"),
                    "direccion": result.get("direccion", "").strip(),
                    "departamento": result.get("departamento", ""),
                    "provincia": result.get("provincia", ""),
                    "distrito": result.get("distrito", ""),
                    "ubigeo": result.get("ubigeo", ""),
                    "fuente": "peruapi_sunat",
                    "fecha_consulta": datetime.now().isoformat()
                }
                cache.set(cache_key, response_data, expire=3600)
                return response_data
            elif result and result.get("code") == "404":
                return {
                    "error": True,
                    "message": "RUC no encontrado en SUNAT",
                    "ruc": ruc
                }
            elif result and result.get("code") == "401":
                return {
                    "error": True,
                    "message": "API Key inválida o IP no autorizada",
                    "ruc": ruc
                }
        
        # No se pudo obtener datos reales
        return {
            "error": True,
            "message": "API no configurada. Configure PERUAPI_TOKEN en las variables de entorno.",
            "ruc": ruc
        }
    
    def get_osce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones OSCE para un RUC.
        Placeholder - implementar cuando Perú API soporte OSCE o tengamos scraper.
        """
        cache_key = f"osce:{ruc}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # TODO: Implementar consulta OSCE cuando esté disponible
        data = []
        cache.set(cache_key, data, expire=7200)
        return data
    
    def get_tce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones TCE para un RUC.
        Placeholder - implementar cuando Perú API soporte TCE o tengamos scraper.
        """
        cache_key = f"tce:{ruc}"
        
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # TODO: Implementar consulta TCE cuando esté disponible
        data = []
        cache.set(cache_key, data, expire=7200)
        return data
    
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
        
        return {
            "ruc": ruc,
            "company_name": sunat_data.get("razon_social", ""),
            "sunat": sunat_data,
            "osce_sanctions": osce_sanctions,
            "tce_sanctions": tce_sanctions,
            "consulted_at": datetime.now().isoformat(),
            "data_sources": ["SUNAT"],
            "real_data": True
        }

# Instancia global
external_api = ExternalAPIService()
