"""
Módulo de ingesta de datos TCE (Tribunal de Contrataciones del Estado).
Actualmente usa scraping limitado hasta encontrar datos abiertos.
"""
import os
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TCEDataIngester:
    """
    Ingestor de datos TCE.
    Nota: El TCE no tiene portal de datos abiertos como OSCE.
    Se implementa con datos de inhabilitaciones judiciales que ya vienen en OSCE.
    """
    
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv('DATABASE_URL')
    
    def sync_tce_flags(self) -> int:
        """
        Actualiza flags de TCE basado en datos de inhabilitaciones judiciales
        que ya están en la tabla osce_risk_data.
        
        Returns:
            Número de registros actualizados
        """
        if not self.db_url:
            logger.error("❌ DATABASE_URL no configurada")
            return 0
        
        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Marcar como TCE las inhabilitaciones que vienen de órganos jurisdiccionales
            cursor.execute("""
                UPDATE osce_risk_data
                SET flag_sancion_tce = TRUE
                WHERE cantidad_inhabilitaciones > 0
                  AND flag_sancion_tce = FALSE;
            """)
            
            updated = cursor.rowcount
            conn.commit()
            
            logger.info(f"✅ Actualizados {updated} registros con flag TCE")
            return updated
            
        except Exception as e:
            logger.error(f"❌ Error actualizando flags TCE: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()
    
    def get_tce_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de sanciones TCE."""
        if not self.db_url:
            return {}
        
        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_con_tce,
                    SUM(CASE WHEN dias_inhabilitacion_restantes > 0 THEN 1 ELSE 0 END) as inhabilitaciones_vigentes,
                    AVG(score_osce_anual) as score_promedio
                FROM osce_risk_data
                WHERE flag_sancion_tce = TRUE;
            """)
            
            row = cursor.fetchone()
            return {
                'total_con_sancion_tce': row[0] or 0,
                'inhabilitaciones_vigentes': row[1] or 0,
                'score_promedio': round(row[2], 2) if row[2] else 0,
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo stats TCE: {e}")
            return {}
        finally:
            if conn:
                conn.close()


# Función para ejecutar desde línea de comandos
if __name__ == '__main__':
    ingester = TCEDataIngester()
    
    # Sync flags TCE
    updated = ingester.sync_tce_flags()
    
    # Get stats
    stats = ingester.get_tce_stats()
    
    print(f"Registros actualizados: {updated}")
    print(f"Estadísticas TCE: {stats}")
