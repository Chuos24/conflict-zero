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
    Fuente primaria: Perú API (peruapi.com)
    """
    
    def __init__(self):
        # Perú API - Fuente primaria
        # Intentar ambas variables de entorno
        self.peruapi_token = os.getenv("PERUAPI_TOKEN") or os.getenv("PERU_API_KEY") or settings.PERUAPI_TOKEN or settings.PERU_API_KEY
        self.peruapi_base_url = "https://peruapi.com"
        
        # Verificar si tenemos API configurada
        self.has_real_api = bool(self.peruapi_token)
        
        # DEBUG: Log para verificar
        print(f"DEBUG: PERUAPI_TOKEN='{os.getenv('PERUAPI_TOKEN', 'NOT_SET')[:10]}...' PERU_API_KEY='{os.getenv('PERU_API_KEY', 'NOT_SET')[:10]}...'")
        print(f"DEBUG: peruapi_token='{self.peruapi_token[:10] if self.peruapi_token else 'EMPTY'}...' has_real_api={self.has_real_api}")
    
    def _call_peru_api(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Llama a BuscarUC API para obtener datos reales de SUNAT"""
        # Leer token cada vez (para detectar cambios en env vars)
        token = os.getenv("PERUAPI_TOKEN") or os.getenv("PERU_API_KEY")
        if not token:
            print(f"DEBUG _call_peru_api: No token found!")
            return None
        
        try:
            # BuscarUC API - POST request
            url = "https://buscaruc.com/api/v1/ruc"
            headers = {"Content-Type": "application/json"}
            payload = {"token": token, "ruc": endpoint.replace("api/ruc/", "")}
            
            print(f"DEBUG: Calling BuscarUC API for RUC: {payload['ruc']}")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            print(f"DEBUG: Response status: {response.status_code}")
            
            data = response.json()
            
            # Convertir respuesta de BuscarUC al formato esperado
            if data.get("error"):
                return {"code": "404", "message": data.get("message", "RUC no encontrado")}
            
            return {
                "code": "200",
                "razon_social": data.get("razonSocial", "") or data.get("nombre", ""),
                "nombre": data.get("nombre", ""),
                "estado": data.get("estado", "ACTIVO"),
                "condicion": data.get("condicion", "HABIDO"),
                "direccion": data.get("direccion", ""),
                "departamento": data.get("departamento", ""),
                "provincia": data.get("provincia", ""),
                "distrito": data.get("distrito", ""),
                "ubigeo": data.get("ubigeo", "")
            }
            
        except requests.exceptions.RequestException as e:
            print(f"Error llamando BuscarUC API: {e}")
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
        
        # Leer token directamente de env vars cada vez
        token = os.getenv("PERUAPI_TOKEN") or os.getenv("PERU_API_KEY")
        print(f"DEBUG get_sunat_data: token={'SET' if token else 'NOT_SET'} len={len(token) if token else 0}")
        
        # Perú API como fuente primaria
        if token:
            print(f"DEBUG: Llamando a _call_peru_api con token válido...")
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

# Instancia global - CREADA PERO NO USADA DIRECTAMENTE
# Usar get_external_api() para obtener una instancia fresca
external_api = ExternalAPIService()

# Función para obtener una instancia fresca (evita problemas de caché en importación)
def get_external_api() -> ExternalAPIService:
    """Retorna una nueva instancia de ExternalAPIService para evitar problemas de caché."""
    return ExternalAPIService()
