#!/usr/bin/env python3
"""
Actualización de sanción OSCE para RUC 20529400790
Actualiza TANTO osce_sanciones_detalle COMO osce_risk_data
"""

import os
import sys

DB_URL = os.environ.get('DATABASE_URL')

def update_sancion_completo():
    """Actualiza la sanción en todas las tablas."""
    
    try:
        from sqlalchemy import create_engine, text
        
        if not DB_URL:
            print("❌ ERROR: DATABASE_URL no configurada")
            return False
        
        engine = create_engine(DB_URL)
        ruc = '20529400790'
        
        with engine.connect() as conn:
            # 1. Actualizar detalle individual
            result_detalle = conn.execute(
                text("""
                    UPDATE osce_sanciones_detalle 
                    SET estado = 'VENCIDA',
                        fecha_fin = '2025-12-31',
                        motivo = COALESCE(motivo, '') || ' | Reducido a 26 meses por Resolución 6981-2025-TCP-S4'
                    WHERE ruc = :ruc AND numero_resolucion LIKE '%4162%'
                    RETURNING id
                """),
                {'ruc': ruc}
            ).fetchone()
            
            if result_detalle:
                print(f"✅ Detalle actualizado (id: {result_detalle[0]})")
            else:
                print("⚠️ No se encontró detalle para actualizar")
            
            # 2. Actualizar tabla agregada osce_risk_data
            result_agg = conn.execute(
                text("""
                    UPDATE osce_risk_data
                    SET sanciones_vigentes = 0,
                        inhabilitaciones_vigentes = 0,
                        dias_inhabilitacion_restantes = 0,
                        flag_sancion_osce = FALSE,
                        score_osce_anual = 95,
                        motivos = COALESCE(motivos, '') || ' | Sanción histórica vencida - Recuperación temporal aplicada'
                    WHERE ruc = :ruc
                    RETURNING ruc
                """),
                {'ruc': ruc}
            ).fetchone()
            
            if result_agg:
                print(f"✅ Tabla agregada actualizada (ruc: {result_agg[0]})")
            else:
                print(f"⚠️ No se encontró registro en osce_risk_data para {ruc}")
                # Intentar insertar
                conn.execute(
                    text("""
                        INSERT INTO osce_risk_data 
                        (ruc, nombre, cantidad_sanciones, cantidad_penalidades, 
                         cantidad_inhabilitaciones, sanciones_vigentes, 
                         inhabilitaciones_vigentes, score_osce_anual, flag_sancion_osce)
                        VALUES (:ruc, 'CONSTRUCTORA ZAMORA JARA SAC', 1, 0, 0, 0, 0, 95, FALSE)
                        ON CONFLICT (ruc) DO UPDATE SET
                            sanciones_vigentes = 0,
                            inhabilitaciones_vigentes = 0,
                            score_osce_anual = 95,
                            flag_sancion_osce = FALSE
                    """),
                    {'ruc': ruc}
                )
                print("✅ Registro creado/actualizado en osce_risk_data")
            
            conn.commit()
            
            # 3. Verificar el cambio
            verify = conn.execute(
                text("""
                    SELECT ruc, sanciones_vigentes, inhabilitaciones_vigentes, 
                           flag_sancion_osce, score_osce_anual
                    FROM osce_risk_data
                    WHERE ruc = :ruc
                """),
                {'ruc': ruc}
            ).fetchone()
            
            if verify:
                print(f"\n📊 Estado final en osce_risk_data:")
                print(f"   RUC: {verify[0]}")
                print(f"   Sanciones vigentes: {verify[1]}")
                print(f"   Inhabilitaciones vigentes: {verify[2]}")
                print(f"   Flag sanción OSCE: {verify[3]}")
                print(f"   Score OSCE: {verify[4]}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = update_sancion_completo()
    sys.exit(0 if success else 1)
