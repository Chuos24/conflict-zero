#!/usr/bin/env python3
"""
Script para scrapear datos de sanciones TCE desde RNP.
URL: https://www.rnp.gob.pe/consultasenlinea/inhabilitados/

Descarga todas las sanciones de los últimos 5 años y las guarda en PostgreSQL.
Uso:
    cd backend && python scripts/rnp_scraper.py

Este script complementa los datos OSCE con sanciones del TCE.
"""
import os
import sys
import re
import time
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup

# Agregar el directorio padre al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal
from sqlalchemy import text


class RNPScraper:
    """
    Scraper para el portal RNP de sanciones TCE.
    Descarga todas las páginas y extrae los datos en formato estructurado.
    """
    
    BASE_URL = "https://www.rnp.gob.pe/consultasenlinea/inhabilitados/busqueda_vnv.asp"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        })
        self.total_registros = 0
        self.registros_procesados = 0
        
    def get_total_pages(self) -> int:
        """
        Obtiene el número total de páginas consultando la primera página.
        """
        try:
            print("[RNP Scraper] Obteniendo total de páginas...")
            response = self.session.get(
                self.BASE_URL,
                params={'action': 'enviar', 'valor': '4'},  # valor=4 = inhabilitaciones
                timeout=30
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar enlaces de paginación
            pagination = soup.find_all('a', href=re.compile(r'pagina=\d+'))
            if pagination:
                # Extraer el número más alto de página
                page_numbers = []
                for link in pagination:
                    match = re.search(r'pagina=(\d+)', link.get('href', ''))
                    if match:
                        page_numbers.append(int(match.group(1)))
                
                if page_numbers:
                    total = max(page_numbers)
                    print(f"[RNP Scraper] Total de páginas encontradas: {total}")
                    return total
            
            # Si no hay paginación, probablemente solo hay 1 página
            return 1
            
        except Exception as e:
            print(f"[RNP Scraper] Error obteniendo total de páginas: {e}")
            return 0
    
    def parse_fecha(self, fecha_str: str) -> Optional[str]:
        """
        Parsea una fecha en formato DD/MM/YYYY a formato ISO.
        """
        if not fecha_str or fecha_str.strip() == '':
            return None
        
        try:
            # Limpiar la fecha
            fecha_str = fecha_str.strip()
            # Parsear DD/MM/YYYY
            dt = datetime.strptime(fecha_str, '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')
        except:
            return None
    
    def parse_monto(self, monto_str: str) -> Optional[float]:
        """
        Parsea un monto en formato peruano (ej: 7,928.10) a float.
        """
        if not monto_str or monto_str.strip() == '':
            return None
        
        try:
            # Limpiar el monto
            monto_str = monto_str.strip().replace(',', '')
            return float(monto_str)
        except:
            return None
    
    def extract_ruc(self, text: str) -> Optional[str]:
        """
        Extrae un RUC de 11 dígitos de un texto.
        """
        if not text:
            return None
        
        # Buscar patrón de 11 dígitos consecutivos
        match = re.search(r'\b(\d{11})\b', text)
        if match:
            return match.group(1)
        return None
    
    def scrape_page(self, page: int) -> List[Dict[str, Any]]:
        """
        Scrapea una página específica del portal RNP.
        
        Returns:
            Lista de diccionarios con los datos extraídos
        """
        registros = []
        
        try:
            print(f"[RNP Scraper] Scrapeando página {page}...")
            
            params = {
                'action': 'enviar',
                'valor': '4',
                'pagina': page
            }
            
            response = self.session.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Buscar la tabla de resultados
            # La tabla tiene columnas: #, Razon Social, RUC, Resolucion, etc.
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                
                for row in rows[1:]:  # Saltar header
                    cells = row.find_all(['td', 'th'])
                    
                    if len(cells) >= 10:  # Asegurar que tiene suficientes columnas
                        try:
                            # Extraer datos de cada celda
                            num = cells[0].get_text(strip=True)
                            razon_social = cells[1].get_text(strip=True)
                            ruc_text = cells[2].get_text(strip=True)
                            resolucion = cells[3].get_text(strip=True)
                            tipo_sancion = cells[4].get_text(strip=True)
                            fecha_desde = cells[5].get_text(strip=True)
                            fecha_hasta = cells[6].get_text(strip=True)
                            infraccion = cells[7].get_text(strip=True)
                            otra_infraccion = cells[8].get_text(strip=True) if len(cells) > 8 else ''
                            norma = cells[9].get_text(strip=True) if len(cells) > 9 else ''
                            estado = cells[10].get_text(strip=True) if len(cells) > 10 else 'VIGENTE'
                            
                            # Extraer RUC
                            ruc = self.extract_ruc(ruc_text)
                            
                            # Combinar infracciones
                            tipo_infraccion = infraccion
                            if otra_infraccion and otra_infraccion != infraccion:
                                tipo_infraccion += f" | {otra_infraccion}"
                            
                            # Parsear fechas
                            fecha_desde_iso = self.parse_fecha(fecha_desde)
                            fecha_hasta_iso = self.parse_fecha(fecha_hasta)
                            
                            # Intentar extraer fecha de resolución del número
                            # Formato típico: 1234-2025-TCP-S1
                            fecha_resolucion = None
                            match_year = re.search(r'(\d{4})', resolucion)
                            if match_year:
                                year = int(match_year.group(1))
                                if 2019 <= year <= 2026:
                                    fecha_resolucion = f"{year}-01-01"  # Aproximación
                            
                            # Determinar si es persona natural (DNI) o jurídica (RUC)
                            if ruc and len(ruc) == 11 and ruc.startswith('10'):
                                # Persona natural con RUC
                                pass
                            elif ruc and len(ruc) == 11:
                                # Empresa
                                pass
                            else:
                                # Sin RUC válido, intentar extraer de otros campos
                                ruc = self.extract_ruc(razon_social) or ruc_text
                            
                            registro = {
                                'ruc': ruc,
                                'razon_social': razon_social,
                                'resolucion': resolucion,
                                'tipo_sancion': tipo_sancion,
                                'fecha_resolucion': fecha_resolucion,
                                'fecha_desde': fecha_desde_iso,
                                'fecha_hasta': fecha_hasta_iso,
                                'tipo_infraccion': tipo_infraccion[:500] if tipo_infraccion else None,  # Limitar longitud
                                'norma': norma[:200] if norma else None,
                                'estado': 'VIGENTE' if 'VIGENTE' in estado.upper() else 'NO VIGENTE',
                                'monto_multa': None,  # No disponible en esta sección
                                'observaciones': None,
                                'fecha_sync': datetime.now()
                            }
                            
                            registros.append(registro)
                            
                        except Exception as e:
                            print(f"[RNP Scraper] Error parseando fila: {e}")
                            continue
            
            print(f"[RNP Scraper] Página {page}: {len(registros)} registros extraídos")
            return registros
            
        except Exception as e:
            print(f"[RNP Scraper] Error en página {page}: {e}")
            return []
    
    def save_to_database(self, registros: List[Dict[str, Any]]) -> int:
        """
        Guarda los registros en PostgreSQL.
        
        Returns:
            Número de registros insertados
        """
        if not registros:
            return 0
        
        db = None
        insertados = 0
        
        try:
            db = SessionLocal()
            
            for reg in registros:
                try:
                    # Usar INSERT ON CONFLICT para evitar duplicados
                    # La clave única es (ruc, resolucion)
                    db.execute(
                        text("""
                            INSERT INTO rnp_tce_sanciones (
                                ruc, razon_social, resolucion, tipo_sancion,
                                fecha_resolucion, fecha_desde, fecha_hasta,
                                tipo_infraccion, norma, estado, monto_multa,
                                observaciones, fecha_sync
                            ) VALUES (
                                :ruc, :razon_social, :resolucion, :tipo_sancion,
                                :fecha_resolucion, :fecha_desde, :fecha_hasta,
                                :tipo_infraccion, :norma, :estado, :monto_multa,
                                :observaciones, :fecha_sync
                            )
                            ON CONFLICT (ruc, resolucion) DO UPDATE SET
                                estado = EXCLUDED.estado,
                                fecha_hasta = EXCLUDED.fecha_hasta,
                                fecha_sync = EXCLUDED.fecha_sync
                        """),
                        reg
                    )
                    insertados += 1
                    
                except Exception as e:
                    print(f"[RNP Scraper] Error insertando registro {reg.get('ruc')}: {e}")
                    continue
            
            db.commit()
            print(f"[RNP Scraper] {insertados} registros guardados en base de datos")
            return insertados
            
        except Exception as e:
            print(f"[RNP Scraper] Error en base de datos: {e}")
            if db:
                db.rollback()
            return 0
        finally:
            if db:
                db.close()
    
    def run(self, max_pages: Optional[int] = None) -> Dict[str, Any]:
        """
        Ejecuta el scraper completo.
        
        Args:
            max_pages: Máximo de páginas a scrapear (None = todas)
        
        Returns:
            Resumen de la ejecución
        """
        print("=" * 60)
        print("RNP TCE SCRAPER - Iniciando")
        print("=" * 60)
        
        inicio = datetime.now()
        
        # Obtener total de páginas
        total_pages = self.get_total_pages()
        
        if max_pages:
            total_pages = min(total_pages, max_pages)
        
        print(f"[RNP Scraper] Procesando {total_pages} páginas...")
        
        total_registros = 0
        
        for page in range(1, total_pages + 1):
            registros = self.scrape_page(page)
            
            if registros:
                insertados = self.save_to_database(registros)
                total_registros += insertados
            
            # Pausa entre páginas para no saturar el servidor
            if page < total_pages:
                time.sleep(2)
            
            # Mostrar progreso cada 5 páginas
            if page % 5 == 0:
                print(f"[RNP Scraper] Progreso: {page}/{total_pages} páginas, {total_registros} registros")
        
        fin = datetime.now()
        duracion = (fin - inicio).total_seconds()
        
        print("=" * 60)
        print("RNP TCE SCRAPER - Completado")
        print(f"Total registros: {total_registros}")
        print(f"Duración: {duracion:.1f} segundos")
        print("=" * 60)
        
        return {
            'total_paginas': total_pages,
            'total_registros': total_registros,
            'duracion_segundos': duracion,
            'inicio': inicio.isoformat(),
            'fin': fin.isoformat()
        }


def main():
    """
    Punto de entrada principal.
    """
    # Verificar si hay argumentos
    max_pages = None
    if len(sys.argv) > 1:
        try:
            max_pages = int(sys.argv[1])
            print(f"[RNP Scraper] Modo prueba: máximo {max_pages} páginas")
        except:
            pass
    
    scraper = RNPScraper()
    resultado = scraper.run(max_pages=max_pages)
    
    print(f"\nResumen:")
    print(f"  - Páginas procesadas: {resultado['total_paginas']}")
    print(f"  - Registros insertados: {resultado['total_registros']}")
    print(f"  - Tiempo: {resultado['duracion_segundos']:.1f}s")
    
    return 0 if resultado['total_registros'] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
