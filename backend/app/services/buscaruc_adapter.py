"""
BuscarUC API Adapter para Conflict Zero
Token: eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE
Plan: Gratuito (154/300 consultas disponibles)
"""

import os
import httpx
from datetime import datetime
from typing import Dict, Optional, Any

# Configuración
BUSCARUC_TOKEN = os.environ.get(
    'BUSCARUC_TOKEN',
    'eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE'
)
BUSCARUC_BASE_URL = "https://buscaruc.com/api/v1"

class BuscarUCAdapter:
    """
    Adapter para consultar datos SUNAT desde BuscarUC API
    Datos actualizados diariamente desde el PADRÓN REDUCIDO de SUNAT
    """
    
    def __init__(self, token: str = None):
        self.token = token or BUSCARUC_TOKEN
    
    async def consultar_ruc(self, ruc: str) -> Optional[Dict[str, Any]]:
        """
        Consulta datos de un RUC en BuscarUC
        Retorna dict con datos de SUNAT
        
        Endpoint: POST https://buscaruc.com/api/v1/ruc
        Body: {"token": "...", "ruc": "..."}
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{BUSCARUC_BASE_URL}/ruc",
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    json={
                        'token': self.token,
                        'ruc': ruc
                    }
                )
                
                if response.status_code == 404:
                    print(f"[BuscarUC] RUC {ruc} no encontrado")
                    return None
                
                if response.status_code == 429:
                    print(f"[BuscarUC] Rate limit alcanzado")
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                # Normalizar datos al formato interno de Conflict Zero
                return self._normalize_data(ruc, data)
                
            except httpx.TimeoutException:
                print(f"[BuscarUC] Timeout consultando {ruc}")
                return None
            except httpx.ConnectError:
                print(f"[BuscarUC] Error de conexión")
                return None
            except Exception as e:
                print(f"[BuscarUC] Error: {e}")
                return None
    
    def _normalize_data(self, ruc: str, buscaruc_data: dict) -> Dict[str, Any]:
        """
        Normaliza los datos de BuscarUC al formato interno de Conflict Zero
        """
        # BuscarUC devuelve datos del PADRÓN REDUCIDO SUNAT
        # Estructura típica: {"ruc": "...", "razon_social": "...", "estado": "...", ...}
        
        return {
            'ruc': ruc,
            'razon_social': buscaruc_data.get('razon_social') or buscaruc_data.get('nombre_o_razon_social', f'Empresa {ruc}'),
            'sunat': {
                'estado': buscaruc_data.get('estado', 'ACTIVO'),
                'condicion': buscaruc_data.get('condicion', 'HABIDO'),
                'direccion': buscaruc_data.get('direccion', ''),
                'departamento': buscaruc_data.get('departamento', ''),
                'provincia': buscaruc_data.get('provincia', ''),
                'distrito': buscaruc_data.get('distrito', ''),
                'actividad_economica': buscaruc_data.get('actividad_economica', []),
            },
            'osce': {
                'total_sanciones': 0,  # BuscarUC no tiene sanciones OSCE
                'sanciones_vigentes': 0,
            },
            'sanciones': [],  # BuscarUC no devuelve sanciones
            'tiene_sanciones': False,
            'fuente': 'BUSCARUC_API',
            'consultor_id': '5470',  # userId del token
            'timestamp_consulta': datetime.now().isoformat()
        }


# Instancia global
buscaruc = BuscarUCAdapter()
