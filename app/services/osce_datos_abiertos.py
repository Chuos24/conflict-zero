"""
Servicio para obtener datos de sanciones OSCE desde PostgreSQL.
Usa SQLAlchemy para compatibilidad con el resto de la aplicación.
"""
import os
import csv
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from app.core.cache import cache
from app.core.database import SessionLocal

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
    
    def get_sanciones_from_db(self, ruc: str) -> Optional[Dict[str, Any]]:
        """
        Consulta sanciones desde PostgreSQL usando SQLAlchemy.
        
        Returns:
            Dict con datos agregados o None si no existe
        """
        db = None
        try:
            db = SessionLocal()
            result = db.execute(
                text("""
                    SELECT ruc, nombre, score_osce_anual, flag_sancion_tce, flag_sancion_osce,
                           cantidad_sanciones, cantidad_penalidades, cantidad_inhabilitaciones,
                           sanciones_vigentes, inhabilitaciones_vigentes, monto_total_penalidades,
                           dias_inhabilitacion_restantes, fecha_ultima_sancion, motivos, fecha_sync
                    FROM osce_risk_data
                    WHERE ruc = :ruc
                """),
                {"ruc": ruc}
            ).fetchone()
            
            if not result:
                return None
            
            return {
                'ruc': result[0],
                'nombre': result[1],
                'score_osce_anual': result[2],
                'flag_sancion_tce': result[3],
                'flag_sancion_osce': result[4],
                'cantidad_sanciones': result[5] or 0,
                'cantidad_penalidades': result[6] or 0,
                'cantidad_inhabilitaciones': result[7] or 0,
                'sanciones_vigentes': result[8] or 0,
                'inhabilitaciones_vigentes': result[9] or 0,
                'monto_total_penalidades': float(result[10]) if result[10] else 0,
                'dias_inhabilitacion_restantes': result[11] or 0,
                'fecha_ultima_sancion': result[12].isoformat() if result[12] else None,
                'motivos': result[13],
                'fecha_sync': result[14].isoformat() if result[14] else None,
            }
        except Exception as e:
            print(f"[OSCE] Error consultando DB: {e}")
            return None
        finally:
            if db:
                db.close()
    
    def get_sanciones_detalle_from_db(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Consulta detalles individuales de sanciones desde PostgreSQL.
        
        Returns:
            Lista de diccionarios con detalles de cada sanción
        """
        db = None
        try:
            db = SessionLocal()
            results = db.execute(
                text("""
                    SELECT id, ruc, tipo_sancion, numero_resolucion, entidad,
                           fecha_inicio, fecha_fin, fecha_corte, motivo,
                           estado, monto_penalidad, objeto_contrato, fuente
                    FROM osce_sanciones_detalle
                    WHERE ruc = :ruc
                    ORDER BY fecha_inicio DESC
                """),
                {"ruc": ruc}
            ).fetchall()
            
            sanciones = []
            for row in results:
                sanciones.append({
                    'id': row[0],
                    'ruc': row[1],
                    'tipo_sancion': row[2],
                    'numero_resolucion': row[3],
                    'entidad': row[4],
                    'fecha_inicio': row[5].isoformat() if row[5] else None,
                    'fecha_fin': row[6].isoformat() if row[6] else None,
                    'fecha_corte': row[7].isoformat() if row[7] else None,
                    'motivo': row[8],
                    'estado': row[9],
                    'monto_penalidad': float(row[10]) if row[10] else None,
                    'objeto_contrato': row[11],
                    'fuente': row[12],
                })
            
            return sanciones
        except Exception as e:
            print(f"[OSCE] Error consultando detalles: {e}")
            return []
        finally:
            if db:
                db.close()
    
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
            print(f"[OSCE] Error leyendo {filename}: {e}")
            return []
    
    def search_sancionados_by_ruc(self, ruc: str) -> List[Dict[str, Any]]:
        """Busca sanciones por RUC en CSV (fallback)."""
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
        """Busca penalidades por RUC en CSV (fallback)."""
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
        """Busca inhabilitaciones judiciales por RUC en CSV (fallback)."""
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
            # Construir respuesta desde DB
            sancionados = []
            penalidades = []
            inhabilitaciones = []
            
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
        # Intentar desde DB primero usando SQLAlchemy
        db = None
        try:
            db = SessionLocal()
            result = db.execute(text("""
                SELECT 
                    COUNT(*),
                    SUM(CASE WHEN flag_sancion_osce THEN 1 ELSE 0 END),
                    SUM(CASE WHEN flag_sancion_tce THEN 1 ELSE 0 END),
                    AVG(score_osce_anual)
                FROM osce_risk_data
            """)).fetchone()
            
            return {
                'total_rucs': result[0] or 0,
                'con_sancion_osce': result[1] or 0,
                'con_sancion_tce': result[2] or 0,
                'score_promedio': round(result[3], 2) if result[3] else 0,
                'fuente': 'postgresql',
            }
        except Exception as e:
            print(f"[OSCE] Error stats DB: {e}")
            # Fallback a CSVs
            stats = {}
            for tipo, filename in self.files.items():
                data = self._read_csv(filename)
                stats[tipo] = len(data)
            stats['fuente'] = 'csv'
            return stats
        finally:
            if db:
                db.close()

# Instancia global
osce_datos_abiertos = OSCEDatosAbiertosService()
