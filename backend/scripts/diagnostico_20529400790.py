#!/usr/bin/env python3
"""
Diagnóstico de RUC 20529400790 - Verificar qué devuelve la DB
"""

import os
import sys

sys.path.insert(0, '/root/.openclaw/workspace/conflict-zero/backend')

def diagnosticar():
    try:
        from app.services.osce_datos_abiertos import osce_datos_abiertos
        
        ruc = '20529400790'
        
        print(f"🔍 Diagnóstico para RUC {ruc}")
        print("=" * 50)
        
        # 1. Verificar datos agregados
        print("\n1. Datos agregados (osce_risk_data):")
        db_data = osce_datos_abiertos.get_sanciones_from_db(ruc)
        if db_data:
            print(f"   sanciones_vigentes: {db_data.get('sanciones_vigentes')}")
            print(f"   cantidad_sanciones: {db_data.get('cantidad_sanciones')}")
            print(f"   score_osce_anual: {db_data.get('score_osce_anual')}")
        else:
            print("   No encontrado")
        
        # 2. Verificar detalles
        print("\n2. Detalles (osce_sanciones_detalle):")
        detalles = osce_datos_abiertos.get_sanciones_detalle_from_db(ruc)
        if detalles:
            print(f"   Total detalles: {len(detalles)}")
            for d in detalles:
                print(f"   - ID: {d.get('id')}")
                print(f"     Resolución: {d.get('numero_resolucion')}")
                print(f"     Estado: {d.get('estado')}")
                print(f"     Fecha fin: {d.get('fecha_fin')}")
        else:
            print("   No encontrado")
        
        # 3. Simular cálculo de scoring
        print("\n3. Simulación de scoring:")
        if db_data and detalles:
            total = db_data['cantidad_sanciones'] + db_data['cantidad_penalidades'] + db_data['cantidad_inhabilitaciones']
            print(f"   Total sanciones: {total}")
            print(f"   Sanciones vigentes: {db_data['sanciones_vigentes']}")
            
            if db_data['sanciones_vigentes'] == 0 and total > 0:
                fechas_fin = [
                    s.get('fecha_fin') for s in detalles 
                    if s.get('fecha_fin') and s.get('estado') == 'VENCIDA'
                ]
                print(f"   Fechas fin VENCIDAS: {fechas_fin}")
                
                if fechas_fin:
                    fecha_mas_reciente = max(fechas_fin)
                    print(f"   Fecha más reciente: {fecha_mas_reciente}")
                    print(f"   ✅ Debería aplicar recuperación temporal")
                else:
                    print(f"   ❌ No hay fechas fin con estado VENCIDA")
                    print(f"   Estados encontrados: {[s.get('estado') for s in detalles]}")
            else:
                print(f"   No aplica recuperación: vigentes={db_data['sanciones_vigentes']}, total={total}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    diagnosticar()
