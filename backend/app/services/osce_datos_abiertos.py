"""
Servicio para obtener datos de sanciones OSCE desde PostgreSQL.
Usa la tabla osce_risk_data poblada por el script de ingesta.
"""
import os
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.cache import cache

class OSCEDatosAbiertosService:
    """
    Servicio para consultar datos de sanciones OSCE.
    Primera fuente: PostgreSQL (tabla osce_risk_data)
    Fallback: Archivos CSV locales
    """
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'osce')
        self.files = {
            'sancionados': 'sancionados_real.csv',
            'penalidades': 'penalidades_real.csv',
            'inhabilitaciones': 'inhabilitaciones_real.csv',
        }
    
    def _get_db_url(self) -> Optional[str]:
        """Obtiene DATABASE_URL dinámicamente."""
        return os.getenv('DATABASE_URL')
    
    def _get_db_connection(self):
        """Obtiene conexión a PostgreSQL."""
        db_url = self._get_db_url()
        if not db_url:
            print("[OSCE] DATABASE_URL no configurado")
            return None
        try:
            import psycopg2
            return psycopg2.connect(db_url)
        except Exception as e:
            print(f"[OSCE] Error conectando a DB: {e}")
            return None
    
    def get_sanciones_from_db(self, ruc: str) -> Optional[Dict[str, Any]]:
        """
        Consulta sanciones desde PostgreSQL (tabla osce_risk_data).
        
        Returns:
            Dict con datos agregados o None si no existe
        """
        conn = None
        try:
            conn = self._get_db_connection()
            if not conn:
                return None
            
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ruc, nombre, score_osce_anual, flag_sancion_tce, flag_sancion_osce,
                       cantidad_sanciones, cantidad_penalidades, cantidad_inhabilitaciones,
                       sanciones_vigentes, inhabilitaciones_vigentes, monto_total_penalidades,
                       dias_inhabilitacion_restantes, fecha_ultima_sancion, motivos, fecha_sync
                FROM osce_risk_data
                WHERE ruc = %s
            """, (ruc,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'ruc': row[0],
                'nombre': row[1],
                'score_osce_anual': row[2],
                'flag_sancion_tce': row[3],
                'flag_sancion_osce': row[4],
                'cantidad_sanciones': row[5] or 0,
                'cantidad_penalidades': row[6] or 0,
                'cantidad_inhabilitaciones': row[7] or 0,
                'sanciones_vigentes': row[8] or 0,
                'inhabilitaciones_vigentes': row[9] or 0,
                'monto_total_penalidades': float(row[10]) if row[10] else 0,
                'dias_inhabilitacion_restantes': row[11] or 0,
                'fecha_ultima_sancion': row[12].isoformat() if row[12] else None,
                'motivos': row[13],
                'fecha_sync': row[14].isoformat() if row[14] else None,
            }
        except Exception as e:
            print(f"Error consultando DB: {e}")
            return None
        finally:
            if conn:
                conn.close()
    
    def _read_csv(self, filename: str) -> List[Dict[str, str]]:
        """Lee un archivo CSV y retorna lista de diccionarios."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            return []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                f.seek(0)
                delimiter = '|' if '|' in first_line else ';' if ';' in first_line else ','
                
                reader = csv.DictReader(f, delimiter=delimiter)
                return list(reader)
        except Exception as e:
            print(f"Error leyendo {filename}: {e}")
            return []
    
    def search_sancionados_by_ruc(self, ruc: str) -> List[Dict[str, Any]]:
        """Busca sanciones por RUC."""
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
        Primero consulta PostgreSQL, luego CSVs como fallback.
        """
        cache_key = f"osce_total:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Intentar obtener desde PostgreSQL primero
        db_data = self.get_sanciones_from_db(ruc)
        
        if db_data:
            # Construir respuesta desde DB (más rápido)
            sancionados = []
            penalidades = []
            inhabilitaciones = []
            
            # Crear entradas sintéticas basadas en los conteos de DB
            if db_data['cantidad_sanciones'] > 0:
                sancionados.append({
                    'tipo': 'sancion_inhabilitacion',
                    'ruc': ruc,
                    'cantidad': db_data['cantidad_sanciones'],
                    'vigentes': db_data['sanciones_vigentes'],
                    'motivos': db_data.get('motivos', ''),
                    'fecha_ultima': db_data.get('fecha_ultima_sancion'),
                })
            
            if db_data['cantidad_penalidades'] > 0:
                penalidades.append({
                    'tipo': 'penalidad',
                    'ruc': ruc,
                    'cantidad': db_data['cantidad_penalidades'],
                    'monto_total': db_data['monto_total_penalidades'],
                })
            
            if db_data['cantidad_inhabilitaciones'] > 0:
                inhabilitaciones.append({
                    'tipo': 'inhabilitacion_judicial',
                    'ruc': ruc,
                    'cantidad': db_data['cantidad_inhabilitaciones'],
                    'vigentes': db_data['inhabilitaciones_vigentes'],
                    'dias_restantes': db_data['dias_inhabilitacion_restantes'],
                })
            
            total = db_data['cantidad_sanciones'] + db_data['cantidad_penalidades'] + db_data['cantidad_inhabilitaciones']
            
            result = {
                'ruc': ruc,
                'total_registros': total,
                'sancionados': sancionados,
                'penalidades': penalidades,
                'inhabilitaciones': inhabilitaciones,
                'tiene_sanciones': total > 0,
                'score_osce': db_data['score_osce_anual'],
                'flag_tce': db_data['flag_sancion_tce'],
                'fecha_consulta': datetime.now().isoformat(),
                'fuente': 'postgresql',
            }
        else:
            # Fallback a CSVs
            sancionados = self.search_sancionados_by_ruc(ruc)
            penalidades = self.search_penalidades_by_ruc(ruc)
            inhabilitaciones = self.search_inhabilitaciones_by_ruc(ruc)
            
            total = len(sancionados) + len(penalidades) + len(inhabilitaciones)
            
            result = {
                'ruc': ruc,
                'total_registros': total,
                'sancionados': sancionados,
                'penalidades': penalidades,
                'inhabilitaciones': inhabilitaciones,
                'tiene_sanciones': total > 0,
                'score_osce': None,
                'flag_tce': len(inhabilitaciones) > 0,
                'fecha_consulta': datetime.now().isoformat(),
                'fuente': 'csv',
            }
        
        cache.set(cache_key, result, expire=1800)
        return result
    
    def get_estadisticas(self) -> Dict[str, Any]:
        """Obtiene estadísticas de los datasets."""
        # Intentar desde DB primero
        conn = self._get_db_connection()
        if conn:
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        COUNT(*),
                        SUM(CASE WHEN flag_sancion_osce THEN 1 ELSE 0 END),
                        SUM(CASE WHEN flag_sancion_tce THEN 1 ELSE 0 END),
                        AVG(score_osce_anual)
                    FROM osce_risk_data
                """)
                row = cursor.fetchone()
                conn.close()
                return {
                    'total_rucs': row[0],
                    'con_sancion_osce': row[1],
                    'con_sancion_tce': row[2],
                    'score_promedio': round(row[3], 2) if row[3] else 0,
                    'fuente': 'postgresql',
                }
            except Exception as e:
                print(f"[OSCE] Error stats DB: {e}")
                conn.close()
        
        # Fallback a CSVs
        stats = {}
        for tipo, filename in self.files.items():
            data = self._read_csv(filename)
            stats[tipo] = len(data)
        stats['fuente'] = 'csv'
        return stats

# Instancia global
osce_datos_abiertos = OSCEDatosAbiertosService()
