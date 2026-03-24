"""
Módulo de ingesta de datos OSCE y TCE para Conflict Zero.
Descarga, procesa y sincroniza datos de sanciones y contrataciones.
"""
import os
import csv
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import execute_values
import logging

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OSCEDataIngester:
    """
    Ingestor de datos OSCE desde archivos CSV de datos abiertos.
    Fuentes: CONOSCE - Portal de Datos Abiertos
    """
    
    # URLs de datasets OSCE (extraídas del portal CONOSCE)
    DATASET_URLS = {
        'sancionados': 'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/sancionados/sancionados.csv',
        'penalidades': 'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/penalidades/penalidades.csv',
        'inhabilitaciones': 'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/inhabilitaciones/inhabilitaciones_judiciales.csv',
    }
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    
    def __init__(self, db_url: Optional[str] = None):
        """
        Inicializa el ingestor.
        
        Args:
            db_url: URL de conexión PostgreSQL (opcional, usa env var DATABASE_URL)
        """
        self.db_url = db_url or os.getenv('DATABASE_URL')
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'osce')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def download_csv(self, dataset_type: str, force: bool = False) -> Optional[str]:
        """
        Descarga un dataset CSV del portal OSCE.
        
        Args:
            dataset_type: Tipo de dataset ('sancionados', 'penalidades', 'inhabilitaciones')
            force: Si True, descarga aunque exista archivo local
            
        Returns:
            Ruta al archivo descargado o None si falla
        """
        if dataset_type not in self.DATASET_URLS:
            logger.error(f"Dataset desconocido: {dataset_type}")
            return None
        
        url = self.DATASET_URLS[dataset_type]
        filepath = os.path.join(self.data_dir, f"{dataset_type}_ingestion.csv")
        
        # Verificar si ya existe y no es force
        if os.path.exists(filepath) and not force:
            logger.info(f"Dataset {dataset_type} ya existe localmente")
            return filepath
        
        try:
            logger.info(f"Descargando {dataset_type} desde OSCE...")
            response = requests.get(url, headers=self.HEADERS, timeout=120)
            response.raise_for_status()
            
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            size_mb = len(response.content) / (1024 * 1024)
            logger.info(f"✅ Descargado {dataset_type}: {size_mb:.2f} MB")
            return filepath
            
        except Exception as e:
            logger.error(f"❌ Error descargando {dataset_type}: {e}")
            return None
    
    def download_all(self, force: bool = False) -> Dict[str, Optional[str]]:
        """Descarga todos los datasets OSCE."""
        results = {}
        for dataset_type in self.DATASET_URLS.keys():
            results[dataset_type] = self.download_csv(dataset_type, force)
        return results
    
    def parse_sancionados(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parsea el CSV de sancionados y extrae datos normalizados.
        
        Returns:
            Lista de dicts con: ruc, nombre, fecha_inicio, fecha_fin, resolucion, motivo
        """
        records = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter='|')
                
                for row in reader:
                    ruc = row.get('RUC', '').strip()
                    if not ruc or len(ruc) != 11:
                        continue
                    
                    # Parsear fechas
                    fecha_inicio = self._parse_date(row.get('FECHA_INICIO', ''))
                    fecha_fin = self._parse_date(row.get('FECHA_FIN', ''))
                    
                    records.append({
                        'ruc': ruc,
                        'nombre': row.get('NOMBRE_RAZONODENOMINACIONSOCIAL', '').strip(),
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin,
                        'resolucion': row.get('NUMERO_RESOLUCION', '').strip(),
                        'motivo': row.get('DE_MOTIVO_INFRACCION', '').strip(),
                        'fecha_corte': row.get('FECHA_CORTE', ''),
                        'vigente': self._is_vigente(fecha_fin),
                    })
        except Exception as e:
            logger.error(f"Error parseando sancionados: {e}")
        
        logger.info(f"📊 Sancionados parseados: {len(records)}")
        return records
    
    def parse_penalidades(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parsea el CSV de penalidades.
        
        Returns:
            Lista de dicts con: ruc, tipo_penalidad, entidad, fecha, monto
        """
        records = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter='|')
                
                for row in reader:
                    ruc = row.get('RUC CONTRATISTA', '').strip()
                    if not ruc or len(ruc) != 11:
                        continue
                    
                    # Parsear monto
                    monto_str = row.get('MONTO', '0').replace(',', '.')
                    try:
                        monto = float(monto_str)
                    except:
                        monto = 0.0
                    
                    records.append({
                        'ruc': ruc,
                        'tipo_penalidad': row.get('TIPO PENALIDAD', '').strip(),
                        'objeto': row.get('OBJETO CONTRATO', '').strip(),
                        'entidad': row.get('ENTIDAD CONTRATANTE', '').strip(),
                        'fecha': row.get('FECHA PENALIDAD', ''),
                        'descripcion': row.get('DESCRIPCION/MOTIVO', '').strip(),
                        'monto': monto,
                    })
        except Exception as e:
            logger.error(f"Error parseando penalidades: {e}")
        
        logger.info(f"📊 Penalidades parseadas: {len(records)}")
        return records
    
    def parse_inhabilitaciones(self, filepath: str) -> List[Dict[str, Any]]:
        """
        Parsea el CSV de inhabilitaciones judiciales.
        
        Returns:
            Lista de dicts con: ruc_dni, nombre, organo, resolucion, fechas
        """
        records = []
        
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f, delimiter='|')
                
                for row in reader:
                    ruc_dni = row.get('RUC_DNI', '').strip()
                    if not ruc_dni:
                        continue
                    
                    # Solo procesar RUCs (11 dígitos), no DNIs
                    if len(ruc_dni) != 11:
                        continue
                    
                    fecha_inicio = self._parse_date(row.get('FECHA_INICIO', ''))
                    fecha_fin = self._parse_date(row.get('FECHA_FIN', ''))
                    
                    # Calcular días restantes
                    dias_restantes = self._calcular_dias_restantes(fecha_fin)
                    
                    records.append({
                        'ruc': ruc_dni,
                        'nombre': row.get('NOMBRE_RAZONODENOMINACIONSOCIAL', '').strip(),
                        'organo': row.get('ORGANO_JURISDICCIONAL', '').strip(),
                        'resolucion': row.get('NUMERO_RESOLUCION', '').strip(),
                        'fecha_inicio': fecha_inicio,
                        'fecha_fin': fecha_fin,
                        'dias_restantes': dias_restantes,
                        'vigente': dias_restantes > 0 if dias_restantes else False,
                    })
        except Exception as e:
            logger.error(f"Error parseando inhabilitaciones: {e}")
        
        logger.info(f"📊 Inhabilitaciones parseadas: {len(records)}")
        return records
    
    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parsea fecha en formato YYYYMMDD a ISO format."""
        if not date_str or len(date_str) != 8:
            return None
        try:
            year = int(date_str[:4])
            month = int(date_str[4:6])
            day = int(date_str[6:8])
            return f"{year}-{month:02d}-{day:02d}"
        except:
            return None
    
    def _is_vigente(self, fecha_fin: Optional[str]) -> bool:
        """Determina si una sanción está vigente basado en fecha_fin."""
        if not fecha_fin:
            return True  # Sin fecha fin = indefinida = vigente
        try:
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            return fin >= datetime.now()
        except:
            return True
    
    def _calcular_dias_restantes(self, fecha_fin: Optional[str]) -> Optional[int]:
        """Calcula días restantes hasta fecha_fin."""
        if not fecha_fin:
            return None
        try:
            fin = datetime.strptime(fecha_fin, '%Y-%m-%d')
            hoy = datetime.now()
            delta = fin - hoy
            return max(0, delta.days)
        except:
            return None
    
    def aggregate_by_ruc(self, sancionados: List[Dict], 
                         penalidades: List[Dict], 
                         inhabilitaciones: List[Dict]) -> Dict[str, Dict[str, Any]]:
        """
        Agrega todos los datos por RUC.
        
        Returns:
            Dict con key=RUC, value=datos agregados
        """
        ruc_data = {}
        
        # Procesar sancionados
        for s in sancionados:
            ruc = s['ruc']
            if ruc not in ruc_data:
                ruc_data[ruc] = {
                    'ruc': ruc,
                    'nombre': s.get('nombre'),
                    'cantidad_sanciones': 0,
                    'cantidad_penalidades': 0,
                    'cantidad_inhabilitaciones': 0,
                    'sanciones_vigentes': 0,
                    'inhabilitaciones_vigentes': 0,
                    'monto_total_penalidades': 0.0,
                    'dias_inhabilitacion_restantes': 0,
                    'tiene_sancion_tce': False,
                    'fecha_ultima_sancion': None,
                    'motivos': [],
                }
            
            ruc_data[ruc]['cantidad_sanciones'] += 1
            if s.get('vigente'):
                ruc_data[ruc]['sanciones_vigentes'] += 1
            
            if s.get('fecha_inicio') > ruc_data[ruc]['fecha_ultima_sancion']:
                ruc_data[ruc]['fecha_ultima_sancion'] = s.get('fecha_inicio')
            
            if s.get('motivo'):
                ruc_data[ruc]['motivos'].append(s['motivo'])
        
        # Procesar penalidades
        for p in penalidades:
            ruc = p['ruc']
            if ruc not in ruc_data:
                ruc_data[ruc] = {
                    'ruc': ruc,
                    'nombre': None,
                    'cantidad_sanciones': 0,
                    'cantidad_penalidades': 0,
                    'cantidad_inhabilitaciones': 0,
                    'sanciones_vigentes': 0,
                    'inhabilitaciones_vigentes': 0,
                    'monto_total_penalidades': 0.0,
                    'dias_inhabilitacion_restantes': 0,
                    'tiene_sancion_tce': False,
                    'fecha_ultima_sancion': None,
                    'motivos': [],
                }
            
            ruc_data[ruc]['cantidad_penalidades'] += 1
            ruc_data[ruc]['monto_total_penalidades'] += p.get('monto', 0)
        
        # Procesar inhabilitaciones
        for i in inhabilitaciones:
            ruc = i['ruc']
            if ruc not in ruc_data:
                ruc_data[ruc] = {
                    'ruc': ruc,
                    'nombre': i.get('nombre'),
                    'cantidad_sanciones': 0,
                    'cantidad_penalidades': 0,
                    'cantidad_inhabilitaciones': 0,
                    'sanciones_vigentes': 0,
                    'inhabilitaciones_vigentes': 0,
                    'monto_total_penalidades': 0.0,
                    'dias_inhabilitacion_restantes': 0,
                    'tiene_sancion_tce': True,  # Judicial = TCE
                    'fecha_ultima_sancion': None,
                    'motivos': [],
                }
            
            ruc_data[ruc]['cantidad_inhabilitaciones'] += 1
            if i.get('vigente'):
                ruc_data[ruc]['inhabilitaciones_vigentes'] += 1
            
            # Tomar el máximo de días restantes
            if i.get('dias_restantes'):
                ruc_data[ruc]['dias_inhabilitacion_restantes'] = max(
                    ruc_data[ruc]['dias_inhabilitacion_restantes'],
                    i['dias_restantes']
                )
        
        return ruc_data
    
    def calcular_score_osce(self, data: Dict[str, Any]) -> int:
        """
        Calcula score OSCE anual basado en datos agregados.
        
        Score 0-100 donde:
        - 100 = Sin sanciones
        - 80-99 = Solo penalidades leves
        - 60-79 = Penalidades múltiples
        - 40-59 = Sanciones con inhabilitación histórica
        - 0-39 = Sanciones vigentes o inhabilitaciones judiciales
        """
        score = 100
        
        # Penalizar por inhabilitaciones judiciales (más graves)
        if data['cantidad_inhabilitaciones'] > 0:
            if data['inhabilitaciones_vigentes'] > 0:
                score -= 60  # Grave: inhabilitación vigente
            else:
                score -= 30  # Histórica pero no vigente
        
        # Penalizar por sanciones OSCE
        if data['sanciones_vigentes'] > 0:
            score -= 40
        elif data['cantidad_sanciones'] > 0:
            score -= 20
        
        # Penalizar por penalidades (monto)
        if data['monto_total_penalidades'] > 100000:
            score -= 20
        elif data['monto_total_penalidades'] > 10000:
            score -= 10
        elif data['monto_total_penalidades'] > 0:
            score -= 5
        
        return max(0, min(100, score))
    
    def sync_to_database(self, ruc_data: Dict[str, Dict[str, Any]]) -> int:
        """
        Sincroniza datos agregados a PostgreSQL usando UPSERT.
        
        Args:
            ruc_data: Dict con datos por RUC
            
        Returns:
            Número de registros sincronizados
        """
        if not self.db_url:
            logger.error("❌ DATABASE_URL no configurada")
            return 0
        
        conn = None
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            
            # Crear tabla si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS osce_risk_data (
                    ruc VARCHAR(11) PRIMARY KEY,
                    nombre VARCHAR(500),
                    score_osce_anual INTEGER DEFAULT 100,
                    flag_sancion_tce BOOLEAN DEFAULT FALSE,
                    flag_sancion_osce BOOLEAN DEFAULT FALSE,
                    cantidad_sanciones INTEGER DEFAULT 0,
                    cantidad_penalidades INTEGER DEFAULT 0,
                    cantidad_inhabilitaciones INTEGER DEFAULT 0,
                    sanciones_vigentes INTEGER DEFAULT 0,
                    inhabilitaciones_vigentes INTEGER DEFAULT 0,
                    monto_total_penalidades DECIMAL(15,2) DEFAULT 0,
                    dias_inhabilitacion_restantes INTEGER DEFAULT 0,
                    fecha_ultima_sancion DATE,
                    motivos TEXT,
                    fecha_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Preparar datos para UPSERT
            values = []
            for ruc, data in ruc_data.items():
                score = self.calcular_score_osce(data)
                values.append((
                    ruc,
                    data.get('nombre'),
                    score,
                    data.get('tiene_sancion_tce', False),
                    data['cantidad_sanciones'] > 0,
                    data['cantidad_sanciones'],
                    data['cantidad_penalidades'],
                    data['cantidad_inhabilitaciones'],
                    data['sanciones_vigentes'],
                    data['inhabilitaciones_vigentes'],
                    data['monto_total_penalidades'],
                    data['dias_inhabilitacion_restantes'],
                    data.get('fecha_ultima_sancion'),
                    '; '.join(data.get('motivos', []))[:1000],
                ))
            
            # UPSERT usando ON CONFLICT
            execute_values(cursor, """
                INSERT INTO osce_risk_data (
                    ruc, nombre, score_osce_anual, flag_sancion_tce, flag_sancion_osce,
                    cantidad_sanciones, cantidad_penalidades, cantidad_inhabilitaciones,
                    sanciones_vigentes, inhabilitaciones_vigentes, monto_total_penalidades,
                    dias_inhabilitacion_restantes, fecha_ultima_sancion, motivos, fecha_sync
                ) VALUES %s
                ON CONFLICT (ruc) DO UPDATE SET
                    nombre = EXCLUDED.nombre,
                    score_osce_anual = EXCLUDED.score_osce_anual,
                    flag_sancion_tce = EXCLUDED.flag_sancion_tce,
                    flag_sancion_osce = EXCLUDED.flag_sancion_osce,
                    cantidad_sanciones = EXCLUDED.cantidad_sanciones,
                    cantidad_penalidades = EXCLUDED.cantidad_penalidades,
                    cantidad_inhabilitaciones = EXCLUDED.cantidad_inhabilitaciones,
                    sanciones_vigentes = EXCLUDED.sanciones_vigentes,
                    inhabilitaciones_vigentes = EXCLUDED.inhabilitaciones_vigentes,
                    monto_total_penalidades = EXCLUDED.monto_total_penalidades,
                    dias_inhabilitacion_restantes = EXCLUDED.dias_inhabilitacion_restantes,
                    fecha_ultima_sancion = EXCLUDED.fecha_ultima_sancion,
                    motivos = EXCLUDED.motivos,
                    fecha_sync = CURRENT_TIMESTAMP;
            """, values)
            
            conn.commit()
            logger.info(f"✅ Sincronizados {len(values)} registros a PostgreSQL")
            return len(values)
            
        except Exception as e:
            logger.error(f"❌ Error sincronizando a DB: {e}")
            if conn:
                conn.rollback()
            return 0
        finally:
            if conn:
                conn.close()
    
    def run_full_sync(self, force_download: bool = False) -> Dict[str, Any]:
        """
        Ejecuta el pipeline completo: descarga, parseo, agregación y sync.
        
        Returns:
            Resumen de la operación
        """
        logger.info("🚀 Iniciando sincronización completa OSCE...")
        
        # 1. Descargar datasets
        downloads = self.download_all(force=force_download)
        
        # 2. Parsear archivos
        sancionados = []
        penalidades = []
        inhabilitaciones = []
        
        if downloads.get('sancionados'):
            sancionados = self.parse_sancionados(downloads['sancionados'])
        
        if downloads.get('penalidades'):
            penalidades = self.parse_penalidades(downloads['penalidades'])
        
        if downloads.get('inhabilitaciones'):
            inhabilitaciones = self.parse_inhabilitaciones(downloads['inhabilitaciones'])
        
        # 3. Agregar por RUC
        ruc_data = self.aggregate_by_ruc(sancionados, penalidades, inhabilitaciones)
        
        # 4. Sincronizar a DB
        synced_count = self.sync_to_database(ruc_data)
        
        result = {
            'success': synced_count > 0,
            'sancionados_parseados': len(sancionados),
            'penalidades_parseadas': len(penalidades),
            'inhabilitaciones_parseadas': len(inhabilitaciones),
            'rucs_unicos': len(ruc_data),
            'registros_sync': synced_count,
            'timestamp': datetime.now().isoformat(),
        }
        
        logger.info(f"✅ Sync completado: {result}")
        return result


# Función para ejecutar desde línea de comandos
if __name__ == '__main__':
    ingester = OSCEDataIngester()
    result = ingester.run_full_sync(force=True)
    print(result)
