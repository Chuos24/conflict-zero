import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.cache import cache

class ScrapingService:
    """
    Servicio para hacer scraping de sanciones OSCE y TCE.
    Consulta directamente las páginas oficiales del Estado Peruano.
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        })
    
    def get_osce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones OSCE para un RUC desde la web oficial.
        URL: https://www.osce.gob.pe/sanciones/
        """
        cache_key = f"osce_scraped:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # OSCE tiene una API/endpoint de consulta
            url = "https://www.osce.gob.pe/sanciones/consulta"
            
            # Intentar con el buscador de sanciones
            params = {
                'ruc': ruc,
                'tipo': 'inhabilitacion'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                sanciones = self._parse_osce_sanciones(soup, ruc)
                
                # Cache por 2 horas
                cache.set(cache_key, sanciones, expire=7200)
                return sanciones
            else:
                print(f"OSCE returned status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error scraping OSCE: {e}")
            return []
    
    def _parse_osce_sanciones(self, soup: BeautifulSoup, ruc: str) -> List[Dict[str, Any]]:
        """Parsea las sanciones OSCE del HTML."""
        sanciones = []
        
        try:
            # Buscar tabla de resultados
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        ruc_cell = cols[0].text.strip()
                        if ruc in ruc_cell:
                            sancion = {
                                'sanction_id': cols[1].text.strip() if len(cols) > 1 else 'N/A',
                                'description': cols[2].text.strip() if len(cols) > 2 else 'Sancion OSCE',
                                'date': cols[3].text.strip() if len(cols) > 3 else None,
                                'status': 'ACTIVA',
                                'severity': 'ALTA',
                                'entity': 'OSCE',
                                'ruc': ruc
                            }
                            sanciones.append(sancion)
            
            # Si no hay tabla, buscar en divs o listas
            if not sanciones:
                resultados = soup.find_all('div', class_='resultado') or soup.find_all('div', class_='sancion')
                for res in resultados:
                    texto = res.get_text()
                    if ruc in texto:
                        sanciones.append({
                            'sanction_id': 'OSCE-' + ruc[-4:],
                            'description': 'Inhabilitacion OSCE detectada',
                            'date': None,
                            'status': 'ACTIVA',
                            'severity': 'ALTA',
                            'entity': 'OSCE',
                            'ruc': ruc
                        })
                        
        except Exception as e:
            print(f"Error parsing OSCE: {e}")
        
        return sanciones
    
    def get_tce_sanctions(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene sanciones TCE para un RUC desde la web oficial.
        URL: https://www.tce.gob.pe/sanciones/
        """
        cache_key = f"tce_scraped:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        try:
            # TCE - Tribunal de Contrataciones del Estado
            url = "https://www.tce.gob.pe/sanciones/"
            
            # El TCE tiene un buscador de sanciones
            params = {
                'busqueda': ruc,
                'tipo': 'inhabilitado'
            }
            
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                sanciones = self._parse_tce_sanciones(soup, ruc)
                
                # Cache por 2 horas
                cache.set(cache_key, sanciones, expire=7200)
                return sanciones
            else:
                print(f"TCE returned status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Error scraping TCE: {e}")
            return []
    
    def _parse_tce_sanciones(self, soup: BeautifulSoup, ruc: str) -> List[Dict[str, Any]]:
        """Parsea las sanciones TCE del HTML."""
        sanciones = []
        
        try:
            # Buscar en tablas
            tables = soup.find_all('table', {'class': ['table', 'dataTable']})
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows[1:]:  # Skip header
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        # Verificar si el RUC está en alguna columna
                        row_text = ' '.join([col.text.strip() for col in cols])
                        if ruc in row_text:
                            sancion = {
                                'sanction_id': cols[0].text.strip() if len(cols) > 0 else 'TCE-' + ruc[-4:],
                                'description': cols[1].text.strip() if len(cols) > 1 else 'Sancion TCE',
                                'date': cols[2].text.strip() if len(cols) > 2 else None,
                                'status': 'ACTIVA',
                                'type': 'INHABILITACION',
                                'entity': 'TCE',
                                'ruc': ruc
                            }
                            sanciones.append(sancion)
            
            # Buscar en divs con clase específica
            if not sanciones:
                sancion_divs = soup.find_all('div', class_=lambda x: x and ('sancion' in x.lower() if x else False))
                for div in sancion_divs:
                    if ruc in div.get_text():
                        sanciones.append({
                            'sanction_id': 'TCE-' + ruc[-4:],
                            'description': 'Inhabilitacion por TCE',
                            'date': None,
                            'status': 'ACTIVA',
                            'type': 'INHABILITACION',
                            'entity': 'TCE',
                            'ruc': ruc
                        })
                        
        except Exception as e:
            print(f"Error parsing TCE: {e}")
        
        return sanciones
    
    def get_infocorp_data(self, ruc: str) -> Dict[str, Any]:
        """
        Obtiene datos de Infocorp/Equifax si están disponibles públicamente.
        Nota: Infocorp requiere suscripción, esto es solo para datos públicos.
        """
        # Por ahora retornar vacío - Infocorp requiere pago
        return {
            'score': None,
            'deuda_total': 0,
            'calificacion': None,
            'fuente': 'no_disponible'
        }

# Instancia global
scraping_service = ScrapingService()