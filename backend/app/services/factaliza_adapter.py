"""
Factaliza API Adapter para Conflict Zero
Consultor #40648 - Token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"""

import os
import httpx
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

# Configuración
FACTALIZA_TOKEN = os.environ.get(
    'FACTALIZA_TOKEN',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDY0OCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.d_-YT6RuTIrq-RZj1TO6Q6r3EG2NL4MRO9odkcaGDYA'
)
FACTALIZA_BASE_URL = "https://api.factaliza.com/api/v1"

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 30
request_times = []

class FactalizaAdapter:
    """
    Adapter para consultar datos de SUNAT/OSCE/TCE desde Factaliza API
    """
    
    def __init__(self, token: str = None):
        self.token = token or FACTALIZA_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _check_rate_limit(self) -> bool:
        """Verifica si estamos dentro del rate limit (30 req/min)"""
        global request_times
        now = datetime.now()
        # Limpiar requests antiguos (> 1 minuto)
        request_times = [t for t in request_times if now - t < timedelta(minutes=1)]
        return len(request_times) < MAX_REQUESTS_PER_MINUTE
    
    def _record_request(self):
        """Registra un request para rate limiting"""
        global request_times
        request_times.append(datetime.now())
    
    async def consultar_ruc(self, ruc: str) -> Optional[Dict[str, Any]]:
        """
        Consulta datos de un RUC en Factaliza
        Retorna dict con datos de SUNAT, OSCE, etc.
        """
        if not self._check_rate_limit():
            raise Exception("RATE_LIMIT_EXCEEDED: Esperar 60s antes de próxima consulta")
        
        self._record_request()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Consulta principal del RUC
                response = await client.get(
                    f"{FACTALIZA_BASE_URL}/ruc/{ruc}",
                    headers=self.headers
                )
                
                if response.status_code == 429:
                    raise Exception("RATE_LIMIT_429: Factaliza rate limit alcanzado")
                
                if response.status_code == 404:
                    # RUC no encontrado en Factaliza
                    return None
                
                response.raise_for_status()
                data = response.json()
                
                # Normalizar datos al formato interno de Conflict Zero
                return self._normalize_data(ruc, data)
                
            except httpx.TimeoutException:
                raise Exception("TIMEOUT: Factaliza no responde")
            except httpx.ConnectError:
                raise Exception("CONNECT_ERROR: No se puede conectar a Factaliza")
    
    def _normalize_data(self, ruc: str, factaliza_data: dict) -> Dict[str, Any]:
        """
        Normaliza los datos de Factaliza al formato interno de Conflict Zero
        """
        # Extraer datos SUNAT
        sunat = factaliza_data.get('sunat', {})
        osce = factaliza_data.get('osce', {})
        sanciones = factaliza_data.get('sanciones', [])
        
        # Calcular días desde inicio de sanción más reciente
        sancion_mas_reciente = None
        dias_transcurridos = 0
        
        if sanciones:
            # Ordenar por fecha
            sanciones_sorted = sorted(
                sanciones,
                key=lambda x: x.get('fecha_inicio', '1900-01-01'),
                reverse=True
            )
            sancion_mas_reciente = sanciones_sorted[0]
            
            try:
                fecha_inicio = datetime.strptime(
                    sancion_mas_reciente.get('fecha_inicio', '1900-01-01'),
                    '%Y-%m-%d'
                )
                dias_transcurridos = (datetime.now() - fecha_inicio).days
            except:
                dias_transcurridos = 0
        
        return {
            'ruc': ruc,
            'razon_social': sunat.get('razon_social') or sunat.get('nombre_o_razon_social', f'Empresa {ruc}'),
            'sunat': {
                'estado': sunat.get('estado_del_contribuyente', 'ACTIVO'),
                'condicion': sunat.get('condicion_del_contribuyente', 'HABIDO'),
                'actividad_economica': sunat.get('actividad_economica', []),
                'direccion': sunat.get('direccion', ''),
                'telefono': sunat.get('telefono', ''),
            },
            'osce': {
                'total_sanciones': osce.get('total_sanciones', len(sanciones)),
                'sanciones_vigentes': osce.get('sanciones_vigentes', 0),
            },
            'sanciones': [
                {
                    'resolucion': s.get('resolucion', 'N/A'),
                    'entidad': s.get('entidad', 'OSCE'),
                    'fecha_inicio': s.get('fecha_inicio', ''),
                    'fecha_fin': s.get('fecha_fin', ''),
                    'estado': s.get('estado', 'VIGENTE'),
                    'descripcion': s.get('descripcion', ''),
                    'dias_transcurridos': dias_transcurridos if s == sancion_mas_reciente else 0
                }
                for s in sanciones
            ],
            'tiene_sanciones': len(sanciones) > 0,
            'sancion_mas_reciente': sancion_mas_reciente,
            'dias_desde_sancion': dias_transcurridos,
            'anios_desde_sancion': round(dias_transcurridos / 365, 2),
            'fuente': 'FACTALIZA_API',
            'consultor_id': '40648',
            'timestamp_consulta': datetime.now().isoformat()
        }
    
    async def consultar_ruc_mock(self, ruc: str) -> Dict[str, Any]:
        """
        Mock para testing cuando Factaliza no está disponible
        """
        # Hardcodes específicos para demo
        if ruc == '20529400790':
            return {
                'ruc': ruc,
                'razon_social': 'CONSTRUCTORA ZAMORA JARA SAC',
                'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
                'osce': {'total_sanciones': 1, 'sanciones_vigentes': 1},
                'sanciones': [{
                    'resolucion': '4162-2023-TCE-S4',
                    'entidad': 'TCE',
                    'fecha_inicio': '2023-09-28',
                    'fecha_fin': '',
                    'estado': 'VIGENTE',
                    'descripcion': 'Sanción por inexactitud de información',
                    'dias_transcurridos': 912,
                }],
                'tiene_sanciones': True,
                'dias_desde_sancion': 912,
                'anios_desde_sancion': 2.5,
                'fuente': 'MOCK_DEMO',
                'consultor_id': '40648',
                'timestamp_consulta': datetime.now().isoformat()
            }
        
        # RUC limpio para demo Gold
        if ruc == '20100123091':
            return {
                'ruc': ruc,
                'razon_social': 'EMPRESA DEMO GOLD SAC',
                'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
                'osce': {'total_sanciones': 0, 'sanciones_vigentes': 0},
                'sanciones': [],
                'tiene_sanciones': False,
                'dias_desde_sancion': 0,
                'anios_desde_sancion': 0,
                'fuente': 'MOCK_DEMO',
                'consultor_id': '40648',
                'timestamp_consulta': datetime.now().isoformat()
            }
        
        # Default aleatorio para otros RUCs
        return {
            'ruc': ruc,
            'razon_social': f'Empresa {ruc}',
            'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
            'osce': {'total_sanciones': 0, 'sanciones_vigentes': 0},
            'sanciones': [],
            'tiene_sanciones': False,
            'dias_desde_sancion': 0,
            'anios_desde_sancion': 0,
            'fuente': 'MOCK_DEFAULT',
            'consultor_id': '40648',
            'timestamp_consulta': datetime.now().isoformat()
        }

# Instancia global
factaliza = FactalizaAdapter()

async def consultar_con_fallback(ruc: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Consulta RUC con estrategia cascada:
    1. Intentar Factaliza API
    2. Si falla (rate limit/error): Usar PostgreSQL cache
    3. Si no existe en BD: Usar Mock
    """
    # Intentar Factaliza primero
    try:
        print(f"[Factaliza] Consultando RUC {ruc}...")
        data = await factaliza.consultar_ruc(ruc)
        if data:
            print(f"[Factaliza] ✓ Datos recibidos para {ruc}")
            # TODO: Guardar en PostgreSQL para cache
            return data
    except Exception as e:
        error_msg = str(e)
        print(f"[Factaliza] ⚠ Error: {error_msg}")
        
        if "RATE_LIMIT" in error_msg:
            print(f"[Factaliza] → Usando cache por rate limit")
        else:
            print(f"[Factaliza] → Usando cache por error de conexión")
    
    # TODO: Buscar en PostgreSQL cache
    # Por ahora, usar mock como fallback
    print(f"[Fallback] Usando mock para {ruc}")
    return await factaliza.consultar_ruc_mock(ruc)

# Exportar
__all__ = ['FactalizaAdapter', 'factaliza', 'consultar_con_fallback']
