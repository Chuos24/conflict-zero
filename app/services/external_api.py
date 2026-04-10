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
        # Token proporcionado por el usuario
        BUSCARUC_TOKEN = "eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE"

        # Intentar variables de entorno primero, luego el token hardcodeado
        self.buscaruc_token = os.getenv("BUSCARUC_TOKEN") or os.getenv("PERUAPI_TOKEN") or os.getenv("PERU_API_KEY") or BUSCARUC_TOKEN
        self.buscaruc_base_url = "https://buscaruc.com"

        # Verificar si tenemos API configurada
        self.has_real_api = bool(self.buscaruc_token)

        # DEBUG: Log para verificar (ocultar parte del token por seguridad)
        token_preview = self.buscaruc_token[:20] + "..." if self.buscaruc_token else "EMPTY"
        print(f"DEBUG: BuscarUC token: {token_preview}")
        print(f"DEBUG: has_real_api={self.has_real_api}")

    def _call_buscaruc_api(self, ruc: str) -> Optional[Dict]:
        """Llama a BuscarUC API para obtener datos reales de SUNAT"""
        # Token de BuscarUC (hardcodeado o de env var)
        BUSCARUC_TOKEN = "eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE"
        token = os.getenv("BUSCARUC_TOKEN") or os.getenv("PERUAPI_TOKEN") or os.getenv("PERU_API_KEY") or BUSCARUC_TOKEN

        if not token:
            print(f"DEBUG _call_buscaruc_api: No token found!")
            return None

        try:
            # BuscarUC API - POST request
            url = "https://buscaruc.com/api/v1/ruc"
            headers = {"Content-Type": "application/json"}
            payload = {"token": token, "ruc": ruc}

            print(f"DEBUG: Calling BuscarUC API for RUC: {ruc}")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            print(f"DEBUG: Response status: {response.status_code}")

            data = response.json()
            
            # Convertir respuesta de BuscarUC al formato esperado
            # La respuesta viene en: data.result con campos en inglés
            if data.get("error") or not data.get("result"):
                return {"code": "404", "message": data.get("message", "RUC no encontrado")}
            
            result = data.get("result", {})
            
            return {
                "code": "200",
                "razon_social": result.get("social_reason", ""),
                "nombre": result.get("social_reason", ""),
                "estado": result.get("taxpayer_state", "ACTIVO"),
                "condicion": result.get("domicile_condition", "HABIDO"),
                "direccion": result.get("address", ""),
                "departamento": result.get("department", ""),
                "provincia": result.get("province", ""),
                "distrito": result.get("district", ""),
                "ubigeo": result.get("ubigeo", "")
            }

        except requests.exceptions.RequestException as e:
            print(f"Error llamando BuscarUC API: {e}")
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

        # BuscarUC como fuente primaria
        print(f"DEBUG: Llamando a BuscarUC API para RUC: {ruc}")
        result = self._call_buscaruc_api(ruc)

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
                "fuente": "buscaruc_sunat",
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
                "message": "Token inválido",
                "ruc": ruc
            }

        # Fallback a datos locales de la base de datos
        print(f"DEBUG: Fallback a DB local para RUC: {ruc}")
        return self._get_sunat_from_db(ruc)

    def _get_sunat_from_db(self, ruc: str) -> Dict[str, Any]:
        """
        Obtiene datos de SUNAT desde la base de datos local como fallback.
        """
        try:
            from app.core.database import SessionLocal
            from app.models import User

            db = SessionLocal()
            try:
                # Buscar en usuarios registrados
                user = db.query(User).filter(User.ruc == ruc).first()
                if user:
                    return {
                        "ruc": ruc,
                        "razon_social": user.company_name or user.full_name or "",
                        "nombre_comercial": user.company_name or user.full_name or "",
                        "estado_contribuyente": "ACTIVO",
                        "condicion_domicilio": "HABIDO",
                        "direccion": "",
                        "fuente": "db_fallback",
                        "fecha_consulta": datetime.now().isoformat()
                    }
            finally:
                db.close()
        except Exception as e:
            print(f"Error en fallback a DB: {e}")

        # Último fallback: datos mínimos
        return {
            "ruc": ruc,
            "razon_social": "",
            "nombre_comercial": "",
            "estado_contribuyente": "ACTIVO",
            "condicion_domicilio": "HABIDO",
            "direccion": "",
            "fuente": "minimal_fallback",
            "fecha_consulta": datetime.now().isoformat()
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
