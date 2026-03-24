import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.cache import cache

class ScrapingService:
    """
    Servicio para obtener sanciones OSCE y TCE.
    Usa datos abiertos del portal CONOSCE cuando está disponible,
    con fallback a scraping web.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def get_osce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones OSCE para un RUC.
        Primero intenta datos abiertos, luego scraping web.
        """
        cache_key = f"osce_sanciones:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        sanciones = []
        
        # Intentar datos abiertos primero
        try:
            from app.services.osce_datos_abiertos import osce_datos_abiertos
            sanciones = osce_datos_abiertos.get_sanciones_por_ruc(ruc)
        except Exception as e:
            print(f"Datos abiertos OSCE no disponibles: {e}")
        
        # Si no hay datos, usar scraping como fallback
        if not sanciones:
            sanciones = self._scrape_osce_sanciones(ruc)
        
        # Cache por 2 horas
        cache.set(cache_key, sanciones, expire=7200)
        return sanciones
    
    def _scrape_osce_sanciones(self, ruc: str) -> List[Dict[str, Any]]:
        """Scraping web de OSCE como fallback."""
        try:
            url = "https://www.osce.gob.pe/sanciones/consulta"
            params = {'ruc': ruc, 'tipo': 'inhabilitacion'}
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                return self._parse_osce_html(soup, ruc)
            
            return []
        except Exception as e:
            print(f"Error scraping OSCE: {e}")
            return []
    
    def _parse_osce_html(self, soup: BeautifulSoup, ruc: str) -> List[Dict[str, Any]]:
        """Parsea HTML de sanciones OSCE."""
        sanciones = []
        
        try:
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        ruc_cell = cols[0].text.strip()
                        if ruc in ruc_cell:
                            sanciones.append({
                                'sanction_id': cols[1].text.strip() if len(cols) > 1 else 'N/A',
                                'description': cols[2].text.strip() if len(cols) > 2 else 'Sancion OSCE',
                                'date': cols[3].text.strip() if len(cols) > 3 else None,
                                'status': 'ACTIVA',
                                'severity': 'ALTA',
                                'entity': 'OSCE',
                                'ruc': ruc
                            })
        except Exception as e:
            print(f"Error parsing OSCE HTML: {e}")
        
        return sanciones
    
    def get_tce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """Obtiene sanciones TCE para un RUC."""
        cache_key = f"tce_sanciones:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            url = "https://www.tce.gob.pe/sanciones/"
            params = {'busqueda': ruc, 'tipo': 'inhabilitado'}
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                sanciones = self._parse_tce_html(soup, ruc)
                
                cache.set(cache_key, sanciones, expire=7200)
                return sanciones
            
            return []
        except Exception as e:
            print(f"Error scraping TCE: {e}")
            return []
    
    def _parse_tce_html(self, soup: BeautifulSoup, ruc: str) -> List[Dict[str, Any]]:
        """Parsea HTML de sanciones TCE."""
        sanciones = []
        
        try:
            tables = soup.find_all('table', {'class': ['table', 'dataTable']})
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        row_text = ' '.join([col.text.strip() for col in cols])
                        if ruc in row_text:
                            sanciones.append({
                                'sanction_id': cols[0].text.strip() if len(cols) > 0 else 'TCE-' + ruc[-4:],
                                'description': cols[1].text.strip() if len(cols) > 1 else 'Sancion TCE',
                                'date': cols[2].text.strip() if len(cols) > 2 else None,
                                'status': 'ACTIVA',
                                'type': 'INHABILITACION',
                                'entity': 'TCE',
                                'ruc': ruc
                            })
        except Exception as e:
            print(f"Error parsing TCE HTML: {e}")
        
        return sanciones

# Instancia global
scraping_service = ScrapingService()
