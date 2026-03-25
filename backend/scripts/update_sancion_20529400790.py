#!/usr/bin/env python3
"""
Actualización de sanción OSCE para RUC 20529400790
Resolución 6981-2025-TCP-S4 redujo la inhabilitación de 37 a 26 meses
Nueva fecha de fin: 31 de diciembre 2025 (ya vencida)
"""

import os
import sys
from datetime import datetime

# Configuración de DB
DB_URL = os.environ.get('DATABASE_URL')

def update_sancion_20529400790():
    """Actualiza la sanción con la resolución de reducción."""
    
    try:
        from sqlalchemy import create_engine, text
        
        if not DB_URL:
            print("❌ ERROR: DATABASE_URL no configurada")
            return False
        
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            # Buscar el registro actual
            result = conn.execute(
                text("SELECT * FROM osce_sanciones_detalle WHERE ruc = :ruc AND numero_resolucion LIKE '%4162%'"),
                {'ruc': '20529400790'}
            ).fetchone()
            
            if not result:
                print("⚠️ No se encontró la sanción 4162-2023-TCE-S4")
                return False
            
            print(f"📋 Registro actual:")
            print(f"   RUC: {result.ruc}")
            print(f"   Resolución: {result.numero_resolucion}")
            print(f"   Fecha inicio: {result.fecha_inicio}")
            print(f"   Fecha fin (actual): {result.fecha_fin}")
            print(f"   Estado: {result.estado}")
            
            # Actualizar con la nueva información
            # Resolución 6981-2025-TCP-S4 establece 26 meses desde 31/oct/2023
            # Nueva fecha fin: 31 de diciembre 2025
            
            nueva_fecha_fin = '2025-12-31'
            nuevo_estado = 'VENCIDA'
            
            conn.execute(
                text("""
                    UPDATE osce_sanciones_detalle 
                    SET fecha_fin = :fecha_fin,
                        estado = :estado,
                        motivo = COALESCE(motivo, '') || ' | Nota: Reducido a 26 meses por Resolución 6981-2025-TCP-S4 (retroactividad benigna)'
                    WHERE id = :id
                """),
                {
                    'fecha_fin': nueva_fecha_fin,
                    'estado': nuevo_estado,
                    'id': result.id
                }
            )
            conn.commit()
            
            print(f"\n✅ Actualizado:")
            print(f"   Nueva fecha fin: {nueva_fecha_fin}")
            print(f"   Nuevo estado: {nuevo_estado}")
            print(f"   Score esperado: ~95 (vencida hace ~3 meses)")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == '__main__':
    success = update_sancion_20529400790()
    sys.exit(0 if success else 1)
