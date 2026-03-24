"""
Servicio para obtener datos de sanciones OSCE desde datos abiertos.
Usa el portal CONOSCE con autenticación pública.
"""
import requests
import csv
import io
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.cache import cache

class OSCEDatosAbiertosService:
    """
    Servicio para consultar datos de sanciones OSCE desde datos abiertos.
    Fuentes:
    - Inhabilitaciones judiciales
    - Sancionados
    - Penalidades
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'es-PE,es;q=0.9',
        })
        
        # URLs base
        self.base_url = "https://bi.seace.gob.pe/pentaho"
        self.public_user = "public"
        self.public_pass = "key"
        
        # Endpoints de datos (desde el portal de datos abiertos)
        self.endpoints = {
            'inhabilitaciones': f"{self.base_url}/api/repos/%3Apublic%3Aportal%3Adataset.html/content?userid={self.public_user}&password={self.public_pass}&pagina=inhabilitaciones",
            'sancionados': f"{self.base_url}/api/repos/%3Apublic%3Aportal%3Adataset.html/content?userid={self.public_user}&password={self.public_pass}&pagina=sancionados",
            'penalidades': f"{self.base_url}/api/repos/%3Apublic%3Aportal%3Adataset.html/content?userid={self.public_user}&password={self.public_pass}&pagina=penalidades",
        }
    
    def _get_csv_download_url(self, page_type: str) -> Optional[str]:
        """
        Obtiene la URL de descarga del CSV desde el portal.
        Las URLs están codificadas en base64 en los enlaces de redirección.
        """
        # URLs directas a los CSV (extraídas del portal)
        csv_urls = {
            'inhabilitaciones': 'https://conosce.osce.gob.pe/portal/assets/67ae6c4a/reportes/inhabilitaciones/inhabilitaciones_judiciales.csv',
            'sancionados': 'https://conosce.osce.gob.pe/portal/assets/67ae6c4a/reportes/sancionados/sancionados.csv',
            'sancionados_multi': 'https://conosce.osce.gob.pe/portal/assets/67ae6c4a/reportes/sancionados/sancionados_multi.csv',
            'penalidades': 'https://conosce.osce.gob.pe/portal/assets/67ae6c4a/reportes/penalidades/penalidades.csv',
        }
        return csv_urls.get(page_type)
    
    def download_csv(self, page_type: str) -> Optional[str]:
        """
        Descarga el CSV de sanciones y retorna el contenido como string.
        """
        cache_key = f"osce_csv:{page_type}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        url = self._get_csv_download_url(page_type)
        if not url:
            return None
        
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code == 200:
                content = response.text
                # Cache por 6 horas
                cache.set(cache_key, content, expire=21600)
                return content
            else:
                print(f"Error descargando CSV {page_type}: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error descargando CSV {page_type}: {e}")
            return None
    
    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parsea el contenido CSV a lista de diccionarios."""
        if not csv_content:
            return []
        
        try:
            # Detectar el delimitador (puede ser ; o ,)
            first_line = csv_content.split('\n')[0]
            delimiter = ';' if ';' in first_line else ','
            
            reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
            return list(reader)
        except Exception as e:
            print(f"Error parseando CSV: {e}")
            return []
    
    def get_sanciones_por_ruc(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene todas las sanciones OSCE para un RUC específico.
        Busca en inhabilitaciones, sancionados y penalidades.
        """
        cache_key = f"osce_sanciones:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        sanciones = []
        
        # Buscar en cada tipo de sanción
        for tipo in ['inhabilitaciones', 'sancionados', 'penalidades']:
            csv_content = self.download_csv(tipo)
            if csv_content:
                registros = self.parse_csv(csv_content)
                for registro in registros:
                    # Buscar el RUC en cualquier campo que parezca ser RUC
                    for key, value in registro.items():
                        if value and ruc in str(value):
                            sanciones.append({
                                'tipo': tipo,
                                'datos': registro,
                                'fecha_extraccion': datetime.now().isoformat()
                            })
                            break
        
        # Cache por 1 hora
        cache.set(cache_key, sanciones, expire=3600)
        return sanciones
    
    def get_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de los datasets."""
        stats = {}
        
        for tipo in ['inhabilitaciones', 'sancionados', 'penalidades']:
            csv_content = self.download_csv(tipo)
            if csv_content:
                registros = self.parse_csv(csv_content)
                stats[tipo] = len(registros)
            else:
                stats[tipo] = 0
        
        return stats

# Instancia global
osce_datos_abiertos = OSCEDatosAbiertosService()
