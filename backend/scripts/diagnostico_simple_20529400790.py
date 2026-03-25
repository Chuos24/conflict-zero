#!/usr/bin/env python3
"""
Diagnóstico simple de RUC 20529400790 - SQL directo
"""

import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get('DATABASE_URL')

def diagnosticar():
    if not DB_URL:
        print("❌ DATABASE_URL no configurada")
        return
    
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        print("🔍 Diagnóstico RUC 20529400790")
        print("=" * 50)
        
        # 1. Verificar osce_risk_data
        print("\n1. Tabla osce_risk_data:")
        result = conn.execute(
            text("SELECT sanciones_vigentes, cantidad_sanciones, score_osce_anual FROM osce_risk_data WHERE ruc = :ruc"),
            {'ruc': '20529400790'}
        ).fetchone()
        
        if result:
            print(f"   sanciones_vigentes: {result[0]}")
            print(f"   cantidad_sanciones: {result[1]}")
            print(f"   score_osce_anual: {result[2]}")
        else:
            print("   ❌ No encontrado")
        
        # 2. Verificar osce_sanciones_detalle
        print("\n2. Tabla osce_sanciones_detalle:")
        results = conn.execute(
            text("SELECT numero_resolucion, estado, fecha_fin FROM osce_sanciones_detalle WHERE ruc = :ruc"),
            {'ruc': '20529400790'}
        ).fetchall()
        
        if results:
            print(f"   Total registros: {len(results)}")
            for row in results:
                print(f"   - {row[0]} | estado: '{row[1]}' | fecha_fin: {row[2]}")
        else:
            print("   ❌ No encontrado")
        
        # 3. Verificar si el scoring debería aplicar recuperación
        print("\n3. Análisis:")
        if result and results:
            vigentes = result[0] or 0
            total = result[1] or 0
            print(f"   Vigentes: {vigentes}, Total: {total}")
            
            if vigentes == 0 and total > 0:
                fechas_vencidas = [r[2] for r in results if r[1] == 'VENCIDA' and r[2]]
                print(f"   Fechas fin con estado VENCIDA: {fechas_vencidas}")
                if fechas_vencidas:
                    print("   ✅ Debería aplicar recuperación temporal")
                else:
                    print("   ❌ No hay fechas con estado VENCIDA")
                    estados = [r[1] for r in results]
                    print(f"   Estados encontrados: {estados}")

if __name__ == '__main__':
    diagnosticar()
