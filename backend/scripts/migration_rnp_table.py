"""
Migración para crear tabla de sanciones RNP/TCE.
Ejecutar: cd backend && python scripts/migration_rnp_table.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import SessionLocal, engine
from sqlalchemy import text


def create_rnp_table():
    """
    Crea la tabla rnp_tce_sanciones con índices optimizados.
    """
    db = SessionLocal()
    
    try:
        print("[Migration] Creando tabla rnp_tce_sanciones...")
        
        # Crear tabla
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS rnp_tce_sanciones (
                id SERIAL PRIMARY KEY,
                ruc VARCHAR(11) NOT NULL,
                razon_social VARCHAR(500),
                resolucion VARCHAR(50) NOT NULL,
                tipo_sancion VARCHAR(20),  -- Definitivo, Temporal, Multa
                fecha_resolucion DATE,
                fecha_desde DATE,
                fecha_hasta DATE,
                tipo_infraccion TEXT,
                norma VARCHAR(200),
                estado VARCHAR(20),  -- VIGENTE, NO VIGENTE
                monto_multa DECIMAL(15, 2),
                observaciones TEXT,
                fecha_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                
                -- Constraint única: un RUC no puede tener la misma resolución duplicada
                CONSTRAINT unique_ruc_resolucion UNIQUE (ruc, resolucion)
            );
        """))
        
        # Crear índices para búsquedas rápidas
        print("[Migration] Creando índices...")
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rnp_ruc ON rnp_tce_sanciones(ruc);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rnp_estado ON rnp_tce_sanciones(estado);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rnp_tipo_sancion ON rnp_tce_sanciones(tipo_sancion);
        """))
        
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_rnp_vigentes ON rnp_tce_sanciones(ruc, estado) 
            WHERE estado = 'VIGENTE';
        """))
        
        db.commit()
        print("[Migration] ✓ Tabla e índices creados exitosamente")
        
        return True
        
    except Exception as e:
        print(f"[Migration] ✗ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_table():
    """
    Verifica que la tabla fue creada correctamente.
    """
    db = SessionLocal()
    
    try:
        result = db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'rnp_tce_sanciones'
        """)).fetchone()
        
        if result and result[0] > 0:
            print("[Migration] ✓ Verificación exitosa: tabla existe")
            
            # Contar registros
            count = db.execute(text("SELECT COUNT(*) FROM rnp_tce_sanciones")).fetchone()
            print(f"[Migration] Registros actuales: {count[0]}")
            
            return True
        else:
            print("[Migration] ✗ Verificación fallida: tabla no existe")
            return False
            
    except Exception as e:
        print(f"[Migration] ✗ Error en verificación: {e}")
        return False
    finally:
        db.close()


def main():
    print("=" * 60)
    print("MIGRACIÓN: Tabla RNP TCE Sanciones")
    print("=" * 60)
    
    if create_rnp_table():
        verify_table()
        print("\n✓ Migración completada exitosamente")
        return 0
    else:
        print("\n✗ Migración fallida")
        return 1


if __name__ == "__main__":
    sys.exit(main())
