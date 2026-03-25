"""
Migration script: Create osce_sanciones_detalle table
Stores individual sanctions with full details
"""
import os
import sys

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text

def migrate():
    """Create detailed sanctions table."""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("❌ DATABASE_URL not set")
        return False
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Create table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS osce_sanciones_detalle (
                id SERIAL PRIMARY KEY,
                ruc VARCHAR(11) NOT NULL,
                tipo_sancion VARCHAR(50) NOT NULL,  -- 'sancion_inhabilitacion', 'penalidad', 'inhabilitacion_judicial'
                numero_resolucion VARCHAR(100),
                entidad VARCHAR(200),  -- Entidad contratante u organo jurisdiccional
                fecha_inicio DATE,
                fecha_fin DATE,
                fecha_corte DATE,
                motivo TEXT,
                estado VARCHAR(20) DEFAULT 'VIGENTE',  -- 'VIGENTE', 'VENCIDA', 'LEVANTADA'
                monto_penalidad DECIMAL(15,2),
                objeto_contrato TEXT,
                fuente VARCHAR(50) DEFAULT 'OSCE',  -- 'OSCE', 'TCE', 'PODER_JUDICIAL'
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_osce_sanciones_ruc 
                ON osce_sanciones_detalle(ruc);
            
            CREATE INDEX IF NOT EXISTS idx_osce_sanciones_tipo 
                ON osce_sanciones_detalle(tipo_sancion);
            
            CREATE INDEX IF NOT EXISTS idx_osce_sanciones_estado 
                ON osce_sanciones_detalle(estado);
            
            CREATE INDEX IF NOT EXISTS idx_osce_sanciones_fecha 
                ON osce_sanciones_detalle(fecha_inicio);
        """))
        
        conn.commit()
        print("✅ Table osce_sanciones_detalle created successfully")
        return True

if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
