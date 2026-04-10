"""
Servicio para obtener datos de sanciones TCE desde RNP (Registro Nacional de Proveedores).
URL: https://www.rnp.gob.pe/consultasenlinea/inhabilitados/

Esta fuente complementa OSCE con sanciones del Tribunal de Contrataciones del Estado (TCE)
que pueden no estar en los datos de OSCE.
"""
import os
import csv
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from app.core.cache import cache
from app.core.database import SessionLocal


class RNPDatosService:
    """
    Servicio para consultar datos de sanciones TCE desde RNP.
    Primera fuente: PostgreSQL (tabla rnp_tce_sanciones)
    Fallback: Scraping directo desde la web
    """
    
    BASE_URL = "https://www.rnp.gob.pe/consultasenlinea/inhabilitados/busqueda_vnv.asp"
    
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data', 'rnp')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def get_sanciones_from_db(self, ruc: str) -> Optional[Dict[str, Any]]:
        """
        Consulta sanciones TCE desde PostgreSQL.
        
        Returns:
            Dict con datos agregados o None si no existe
        """
        db = None
        try:
            db = SessionLocal()
            result = db.execute(
                text("""
                    SELECT 
                        ruc, 
                        razon_social, 
                        COUNT(*) as cantidad_sanciones,
                        COUNT(CASE WHEN estado = 'VIGENTE' THEN 1 END) as sanciones_vigentes,
                        COUNT(CASE WHEN tipo_sancion = 'Definitivo' THEN 1 END) as sanciones_definitivas,
                        COUNT(CASE WHEN tipo_sancion = 'Temporal' THEN 1 END) as sanciones_temporales,
                        SUM(CASE WHEN monto_multa IS NOT NULL THEN monto_multa ELSE 0 END) as monto_total_multas,
                        MAX(CASE WHEN estado = 'VIGENTE' THEN fecha_hasta END) as fecha_maxima_vigencia,
                        ARRAY_AGG(DISTINCT tipo_infraccion) as tipos_infraccion,
                        MAX(fecha_sync) as fecha_sync
                    FROM rnp_tce_sanciones
                    WHERE ruc = :ruc
                    GROUP BY ruc, razon_social
                """),
                {"ruc": ruc}
            ).fetchone()
            
            if not result:
                return None
            
            return {
                'ruc': result[0],
                'razon_social': result[1],
                'cantidad_sanciones': result[2] or 0,
                'sanciones_vigentes': result[3] or 0,
                'sanciones_definitivas': result[4] or 0,
                'sanciones_temporales': result[5] or 0,
                'monto_total_multas': float(result[6]) if result[6] else 0.0,
                'fecha_maxima_vigencia': result[7],
                'tipos_infraccion': result[8] if result[8] else [],
                'fuente': 'rnp_tce',
                'fecha_sync': result[9]
            }
            
        except Exception as e:
            print(f"[RNP] Error consultando DB: {e}")
            return None
        finally:
            if db:
                db.close()
    
    def get_sanciones_detalle(self, ruc: str) -> List[Dict[str, Any]]:
        """
        Obtiene el detalle completo de sanciones para un RUC.
        
        Returns:
            Lista de diccionarios con cada sanción
        """
        db = None
        try:
            db = SessionLocal()
            results = db.execute(
                text("""
                    SELECT 
                        ruc, razon_social, resolucion, tipo_sancion,
                        fecha_resolucion, fecha_desde, fecha_hasta,
                        tipo_infraccion, norma, estado, monto_multa,
                        observaciones
                    FROM rnp_tce_sanciones
                    WHERE ruc = :ruc
                    ORDER BY fecha_resolucion DESC
                """),
                {"ruc": ruc}
            ).fetchall()
            
            return [
                {
                    'ruc': row[0],
                    'razon_social': row[1],
                    'resolucion': row[2],
                    'tipo_sancion': row[3],
                    'fecha_resolucion': row[4],
                    'fecha_desde': row[5],
                    'fecha_hasta': row[6],
                    'tipo_infraccion': row[7],
                    'norma': row[8],
                    'estado': row[9],
                    'monto_multa': float(row[10]) if row[10] else None,
                    'observaciones': row[11],
                    'fuente': 'RNP-TCE'
                }
                for row in results
            ]
            
        except Exception as e:
            print(f"[RNP] Error consultando detalle: {e}")
            return []
        finally:
            if db:
                db.close()
    
    def check_sanciones_realtime(self, ruc: str) -> Dict[str, Any]:
        """
        Verifica sanciones en tiempo real consultando RNP.
        Usa cache de 24 horas para no saturar el servicio.
        
        Returns:
            Dict con resultado de la consulta
        """
        cache_key = f"rnp_check:{ruc}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        
        # Por ahora retornamos datos de DB, el scraper se implementará después
        db_result = self.get_sanciones_from_db(ruc)
        
        result = {
            'ruc': ruc,
            'encontrado': db_result is not None,
            'datos': db_result or {},
            'consulta_en_tiempo_real': False,
            'mensaje': 'Datos desde base de datos local. Scraper en desarrollo.'
        }
        
        cache.set(cache_key, result, ttl=86400)  # 24 horas
        return result
    
    def calcular_score_rnp(self, datos: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calcula un score de riesgo basado en datos RNP.
        
        Scoring CRUDO para compliance:
        - Definitiva + Vigente = Score 20 (crítico)
        - Temporal + Vigente = Score 40 (alto)
        - No vigente = Score 70 (histórico)
        - Sin sanciones = Score 100
        
        Returns:
            Dict con score y análisis
        """
        if not datos or datos.get('cantidad_sanciones', 0) == 0:
            return {
                'score': 100,
                'nivel_riesgo': 'low',
                'tiene_sanciones': False,
                'factores': ['Sin sanciones TCE registradas']
            }
        
        factores = []
        score_base = 100
        
        # Penalización por sanciones definitivas
        if datos.get('sanciones_definitivas', 0) > 0:
            score_base = min(score_base, 20)
            factores.append(f"⚠️ {datos['sanciones_definitivas']} sanción(es) DEFINITIVA(S)")
        
        # Penalización por sanciones temporales vigentes
        elif datos.get('sanciones_temporales', 0) > 0 and datos.get('sanciones_vigentes', 0) > 0:
            score_base = min(score_base, 40)
            factores.append(f"⚠️ {datos['sanciones_temporales']} sanción(es) TEMPORAL(ES) vigente(s)")
        
        # Sanciones históricas (no vigentes)
        elif datos.get('cantidad_sanciones', 0) > 0:
            score_base = min(score_base, 70)
            factores.append(f"ℹ️ {datos['cantidad_sanciones']} sanción(es) histórica(s) - no vigentes")
        
        # Penalización por monto de multas
        monto = datos.get('monto_total_multas', 0)
        if monto > 100000:
            score_base -= 10
            factores.append(f"💰 Multas elevadas: S/ {monto:,.2f}")
        elif monto > 0:
            factores.append(f"💰 Multas: S/ {monto:,.2f}")
        
        # Determinar nivel de riesgo
        if score_base <= 30:
            nivel = 'critical'
        elif score_base <= 50:
            nivel = 'high'
        elif score_base <= 70:
            nivel = 'medium'
        else:
            nivel = 'low'
        
        return {
            'score': max(0, score_base),
            'nivel_riesgo': nivel,
            'tiene_sanciones': True,
            'cantidad_sanciones': datos.get('cantidad_sanciones', 0),
            'sanciones_vigentes': datos.get('sanciones_vigentes', 0),
            'sanciones_definitivas': datos.get('sanciones_definitivas', 0),
            'monto_total_multas': datos.get('monto_total_multas', 0),
            'factores': factores,
            'fecha_maxima_vigencia': datos.get('fecha_maxima_vigencia')
        }


# Instancia global
rnp_service = RNPDatosService()
