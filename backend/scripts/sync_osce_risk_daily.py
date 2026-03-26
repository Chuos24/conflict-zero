#!/usr/bin/env python3
"""
Script de sincronización diaria OSCE
Recalcula osce_risk_data desde osce_sanciones_detalle
Aplica fórmula de recuperación temporal automáticamente
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

DB_URL = os.environ.get('DATABASE_URL')

def calcular_score_recuperacion(fecha_fin_str: str) -> float:
    """Fórmula 'cruda pero justa' para recuperación temporal."""
    if not fecha_fin_str:
        return 75.0
    
    try:
        if 'T' in fecha_fin_str:
            fecha_fin = datetime.fromisoformat(fecha_fin_str.replace('Z', '+00:00'))
        else:
            fecha_fin = datetime.strptime(fecha_fin_str, '%Y-%m-%d')
        
        hoy = datetime.now()
        dias_transcurridos = (hoy - fecha_fin).days
        años_transcurridos = dias_transcurridos / 365.25
        
        if años_transcurridos >= 3:
            return 95.0
        elif años_transcurridos >= 1:
            progreso = (años_transcurridos - 1) / 2
            return 75 + (progreso * 20)
        else:
            return 75.0
    except:
        return 75.0

def sync_osce_risk_data():
    """Sincroniza datos agregados desde detalles."""
    
    try:
        engine = create_engine(DB_URL)
        
        with engine.connect() as conn:
            print("🔍 Analizando sanciones...")
            
            # Obtener todos los RUCs con sanciones
            rucs = conn.execute(text("""
                SELECT DISTINCT ruc FROM osce_sanciones_detalle
            """)).fetchall()
            
            print(f"📊 {len(rucs)} RUCs con sanciones encontrados")
            
            actualizados = 0
            errores = 0
            
            for (ruc,) in rucs:
                try:
                    # Obtener detalles del RUC
                    detalles = conn.execute(text("""
                        SELECT tipo_sancion, estado, fecha_fin, monto_penalidad
                        FROM osce_sanciones_detalle
                        WHERE ruc = :ruc
                    """), {'ruc': ruc}).fetchall()
                    
                    # Calcular métricas
                    total_sanciones = len(detalles)
                    sanciones_vigentes = sum(1 for d in detalles if d[1] == 'VIGENTE')
                    inhabilitaciones_vigentes = sum(1 for d in detalles 
                        if d[1] == 'VIGENTE' and d[0] in ['inhabilitacion', 'inhabilitacion_judicial'])
                    
                    # Verificar si todas están vencidas (recuperación temporal)
                    todas_vencidas = all(d[1] == 'VENCIDA' for d in detalles)
                    
                    if todas_vencidas and total_sanciones > 0:
                        # Aplicar recuperación temporal
                        fechas_fin = [d[2] for d in detalles if d[2]]
                        if fechas_fin:
                            fecha_mas_reciente = max(fechas_fin)
                            score_osce = calcular_score_recuperacion(fecha_mas_reciente)
                        else:
                            score_osce = 75.0
                    elif sanciones_vigentes > 0:
                        # Score base para sanciones vigentes
                        score_osce = 60.0
                    else:
                        score_osce = 100.0
                    
                    monto_total = sum(d[3] or 0 for d in detalles)
                    
                    # Upsert en osce_risk_data
                    conn.execute(text("""
                        INSERT INTO osce_risk_data (
                            ruc, cantidad_sanciones, cantidad_penalidades, 
                            cantidad_inhabilitaciones, sanciones_vigentes,
                            inhabilitaciones_vigentes, monto_total_penalidades,
                            score_osce_anual, flag_sancion_osce, fecha_sync
                        )
                        SELECT 
                            :ruc,
                            (SELECT COUNT(*) FROM osce_sanciones_detalle WHERE ruc = :ruc AND tipo_sancion = 'sancion'),
                            (SELECT COUNT(*) FROM osce_sanciones_detalle WHERE ruc = :ruc AND tipo_sancion = 'penalidad'),
                            (SELECT COUNT(*) FROM osce_sanciones_detalle WHERE ruc = :ruc AND tipo_sancion = 'inhabilitacion'),
                            :sanciones_vigentes,
                            :inhabilitaciones_vigentes,
                            :monto_total,
                            :score_osce,
                            :flag_sancion,
                            NOW()
                        ON CONFLICT (ruc) DO UPDATE SET
                            cantidad_sanciones = EXCLUDED.cantidad_sanciones,
                            cantidad_penalidades = EXCLUDED.cantidad_penalidades,
                            cantidad_inhabilitaciones = EXCLUDED.cantidad_inhabilitaciones,
                            sanciones_vigentes = EXCLUDED.sanciones_vigentes,
                            inhabilitaciones_vigentes = EXCLUDED.inhabilitaciones_vigentes,
                            monto_total_penalidades = EXCLUDED.monto_total_penalidades,
                            score_osce_anual = EXCLUDED.score_osce_anual,
                            flag_sancion_osce = EXCLUDED.flag_sancion_osce,
                            fecha_sync = NOW()
                    """), {
                        'ruc': ruc,
                        'sanciones_vigentes': sanciones_vigentes,
                        'inhabilitaciones_vigentes': inhabilitaciones_vigentes,
                        'monto_total': monto_total,
                        'score_osce': score_osce,
                        'flag_sancion': sanciones_vigentes > 0
                    })
                    
                    actualizados += 1
                    
                except Exception as e:
                    print(f"❌ Error en RUC {ruc}: {e}")
                    errores += 1
            
            conn.commit()
            
            print(f"\n✅ Sincronización completada:")
            print(f"   - {actualizados} RUCs actualizados")
            print(f"   - {errores} errores")
            
            return True
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = sync_osce_risk_data()
    sys.exit(0 if success else 1)
