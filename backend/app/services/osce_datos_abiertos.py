"""
Servicio para obtener datos de sanciones OSCE desde datos abiertos.
Usa archivos CSV descargados del portal CONOSCE.
"""
import csv
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.cache import cache

class OSCEDatosAbiertosService:
    """
    Servicio para consultar datos de sanciones OSCE desde datos abiertos.
    Fuentes:
    - Sancionados con inhabilitación
    - Penalidades
    - Inhabilitaciones judiciales
    """
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'osce')
        self.files = {
            'sancionados': 'sancionados_real.csv',
            'penalidades': 'penalidades_real.csv',
            'inhabilitaciones': 'inhabilitaciones_real.csv',
        }
    
    def _read_csv(self, filename: str) -> List[Dict[str, str]]:
        """Lee un archivo CSV y retorna lista de diccionarios."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                # Detectar delimitador
                first_line = f.readline()
                f.seek(0)
                delimiter = '|' if '|' in first_line else ';' if ';' in first_line else ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                return list(reader)
        except Exception as e:
            print(f"Error leyendo {filename}: {e}")
            return []
    
    def search_sancionados_by_ruc(self, ruc: str) -> List[Dict[str, Any]]:
        """Busca sanciones por RUC en el archivo de sancionados."""
        cache_key = f"osce_sancionados:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        data = self._read_csv(self.files['sancionados'])
        
        for row in data:
            if row.get('RUC') == ruc:
                results.append({
                    'tipo': 'sancion_inhabilitacion',
                    'ruc': row.get('RUC'),
                    'nombre': row.get('NOMBRE_RAZONODENOMINACIONSOCIAL'),
                    'fecha_inicio': row.get('FECHA_INICIO'),
                    'fecha_fin': row.get('FECHA_FIN'),
                    'resolucion': row.get('NUMERO_RESOLUCION'),
                    'motivo': row.get('DE_MOTIVO_INFRACCION'),
                    'fecha_corte': row.get('FECHA_CORTE'),
                })
        
        cache.set(cache_key, results, expire=3600)
        return results
    
    def search_penalidades_by_ruc(self, ruc: str) -> List[Dict[str, Any]]:
        """Busca penalidades por RUC."""
        cache_key = f"osce_penalidades:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        data = self._read_csv(self.files['penalidades'])
        
        for row in data:
            if row.get('RUC CONTRATISTA') == ruc:
                results.append({
                    'tipo': 'penalidad',
                    'ruc': row.get('RUC CONTRATISTA'),
                    'tipo_penalidad': row.get('TIPO PENALIDAD'),
                    'objeto': row.get('OBJETO CONTRATO'),
                    'entidad': row.get('ENTIDAD CONTRATANTE'),
                    'fecha': row.get('FECHA PENALIDAD'),
                    'descripcion': row.get('DESCRIPCION/MOTIVO'),
                    'monto': row.get('MONTO'),
                })
        
        cache.set(cache_key, results, expire=3600)
        return results
    
    def search_inhabilitaciones_by_ruc(self, ruc: str) -> List[Dict[str, Any]]:
        """Busca inhabilitaciones judiciales por RUC."""
        cache_key = f"osce_inhabilitaciones:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        results = []
        data = self._read_csv(self.files['inhabilitaciones'])
        
        for row in data:
            # El campo es RUC_DNI, puede contener RUC o DNI
            if row.get('RUC_DNI') == ruc:
                results.append({
                    'tipo': 'inhabilitacion_judicial',
                    'ruc_dni': row.get('RUC_DNI'),
                    'nombre': row.get('NOMBRE_RAZONODENOMINACIONSOCIAL'),
                    'organo': row.get('ORGANO_JURISDICCIONAL'),
                    'resolucion': row.get('NUMERO_RESOLUCION'),
                    'fecha_inicio': row.get('FECHA_INICIO'),
                    'fecha_fin': row.get('FECHA_FIN'),
                    'fecha_corte': row.get('FECHA_CORTE'),
                })
        
        cache.set(cache_key, results, expire=3600)
        return results
    
    def get_sanciones_por_ruc(self, ruc: str) -> Dict[str, Any]:
        """
        Obtiene TODAS las sanciones OSCE para un RUC.
        Combina sancionados, penalidades e inhabilitaciones.
        """
        cache_key = f"osce_total:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        sancionados = self.search_sancionados_by_ruc(ruc)
        penalidades = self.search_penalidades_by_ruc(ruc)
        inhabilitaciones = self.search_inhabilitaciones_by_ruc(ruc)
        
        total_sanciones = len(sancionados) + len(penalidades) + len(inhabilitaciones)
        
        result = {
            'ruc': ruc,
            'total_registros': total_sanciones,
            'sancionados': sancionados,
            'penalidades': penalidades,
            'inhabilitaciones': inhabilitaciones,
            'tiene_sanciones': total_sanciones > 0,
            'fecha_consulta': datetime.now().isoformat(),
        }
        
        cache.set(cache_key, result, expire=1800)  # 30 minutos
        return result
    
    def get_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de los datasets cargados."""
        stats = {}
        
        for tipo, filename in self.files.items():
            data = self._read_csv(filename)
            stats[tipo] = len(data)
        
        return stats

# Instancia global
osce_datos_abiertos = OSCEDatosAbiertosService()
