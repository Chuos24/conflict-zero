#!/usr/bin/env python3
"""
Auditor de Sanciones - Detecta casos problemáticos antes de que afecten scores
Ejecutar semanalmente para identificar sanciones que necesitan revisión manual
"""

import os
import sys
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

DB_URL = os.environ.get('DATABASE_URL')

def auditar_sanciones():
    """Detecta sanciones con inconsistencias o que necesitan revisión."""
    
    try:
        engine = create_engine(DB_URL)
        alertas = []
        
        with engine.connect() as conn:
            print("🔍 Iniciando auditoría de sanciones...\n")
            
            # 1. Sanciones marcadas como VIGENTES pero con fecha_fin en el pasado
            # (Deberían ser VENCIDAS automáticamente)
            resultado1 = conn.execute(text("""
                SELECT ruc, numero_resolucion, fecha_fin, estado, entidad, motivo
                FROM osce_sanciones_detalle
                WHERE estado = 'VIGENTE'
                  AND fecha_fin IS NOT NULL
                  AND fecha_fin < CURRENT_DATE
                ORDER BY fecha_fin DESC
            """)).fetchall()
            
            if resultado1:
                alertas.append({
                    'tipo': 'VENCIDAS_NO_ACTUALIZADAS',
                    'cantidad': len(resultado1),
                    'descripcion': 'Sanciones con fecha fin pasada pero aún marcadas como VIGENTES',
                    'ejemplos': [
                        {'ruc': r[0], 'resolucion': r[1], 'fecha_fin': str(r[2]), 'entidad': r[4], 'motivo': r[5]}
                        for r in resultado1[:5]  # Top 5
                    ],
                    'accion': 'Ejecutar script de sincronización para auto-corregir'
                })
            
            # 2. Sanciones VENCIDAS recientemente (< 6 meses) — revisar si aplican recuperación
            resultado2 = conn.execute(text("""
                SELECT ruc, numero_resolucion, fecha_fin, estado, entidad, motivo
                FROM osce_sanciones_detalle
                WHERE estado = 'VENCIDA'
                  AND fecha_fin IS NOT NULL
                  AND fecha_fin >= CURRENT_DATE - INTERVAL '6 months'
                  AND (motivo IS NULL OR motivo NOT LIKE '%recuperación%')
                ORDER BY fecha_fin DESC
            """)).fetchall()
            
            if resultado2:
                alertas.append({
                    'tipo': 'VENCIDAS_RECIENTES',
                    'cantidad': len(resultado2),
                    'descripcion': 'Sanciones vencidas en los últimos 6 meses que podrían necesitar nota de recuperación',
                    'ejemplos': [
                        {'ruc': r[0], 'resolucion': r[1], 'fecha_fin': str(r[2]), 'entidad': r[4]}
                        for r in resultado2[:3]
                    ],
                    'accion': 'Verificar si hay resoluciones judiciales que modificaron fechas'
                })
            
            # 3. Sanciones con fecha_fin NULL pero marcadas como VENCIDAS
            # (Inconsistencia de datos)
            resultado3 = conn.execute(text("""
                SELECT ruc, numero_resolucion, estado, entidad, motivo
                FROM osce_sanciones_detalle
                WHERE estado = 'VENCIDA'
                  AND fecha_fin IS NULL
                LIMIT 10
            """)).fetchall()
            
            if resultado3:
                alertas.append({
                    'tipo': 'FECHAS_FALTANTES',
                    'cantidad': len(resultado3),
                    'descripcion': 'Sanciones VENCIDAS sin fecha_fin (inconsistencia)',
                    'ejemplos': [
                        {'ruc': r[0], 'resolucion': r[1], 'entidad': r[3]}
                        for r in resultado3[:5]
                    ],
                    'accion': 'Investigar y completar fecha_fin manualmente'
                })
            
            # 4. RUCs con múltiples sanciones vigentes (casos complejos)
            resultado4 = conn.execute(text("""
                SELECT ruc, COUNT(*) as cantidad, MAX(entidad) as entidad
                FROM osce_sanciones_detalle
                WHERE estado = 'VIGENTE'
                GROUP BY ruc
                HAVING COUNT(*) > 2
                ORDER BY cantidad DESC
                LIMIT 5
            """)).fetchall()
            
            if resultado4:
                alertas.append({
                    'tipo': 'MULTIPLES_SANCIONES',
                    'cantidad': len(resultado4),
                    'descripcion': 'RUCs con más de 2 sanciones vigentes (revisar si no son duplicados)',
                    'ejemplos': [
                        {'ruc': r[0], 'cantidad': r[1], 'entidad': r[2]}
                        for r in resultado4
                    ],
                    'accion': 'Verificar si son sanciones independientes o duplicados'
                })
            
            # 5. Discrepancia entre tablas (osce_sanciones_detalle vs osce_risk_data)
            resultado5 = conn.execute(text("""
                SELECT d.ruc, d.estado as estado_detalle, 
                       COALESCE(r.sanciones_vigentes, 0) as vigentes_risk
                FROM osce_sanciones_detalle d
                LEFT JOIN osce_risk_data r ON d.ruc = r.ruc
                WHERE d.estado = 'VIGENTE'
                GROUP BY d.ruc, d.estado, r.sanciones_vigentes
                HAVING COALESCE(r.sanciones_vigentes, 0) = 0
                LIMIT 10
            """)).fetchall()
            
            if resultado5:
                alertas.append({
                    'tipo': 'DISCREPANCIA_TABLAS',
                    'cantidad': len(resultado5),
                    'descripcion': 'RUCs con sanciones VIGENTES en detalle pero 0 en tabla agregada',
                    'ejemplos': [{'ruc': r[0]} for r in resultado5[:5]],
                    'accion': 'URGENTE: Ejecutar sync_osce_risk_daily.py'
                })
            
            # Reporte final
            print("=" * 60)
            print("📊 REPORTE DE AUDITORÍA")
            print("=" * 60)
            print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
            print(f"Alertas encontradas: {len(alertas)}\n")
            
            if not alertas:
                print("✅ No se detectaron problemas. Todo está correcto.")
                return True
            
            for i, alerta in enumerate(alertas, 1):
                print(f"\n{'🔴' if alerta['tipo'] in ['DISCREPANCIA_TABLAS', 'FECHAS_FALTANTES'] else '🟡'} ALERTA #{i}: {alerta['tipo']}")
                print(f"   Cantidad: {alerta['cantidad']} casos")
                print(f"   Descripción: {alerta['descripcion']}")
                print(f"   Acción recomendada: {alerta['accion']}")
                if alerta.get('ejemplos'):
                    print(f"   Ejemplos: {alerta['ejemplos'][:3]}")
            
            print("\n" + "=" * 60)
            print("💡 RESUMEN DE ACCIONES:")
            print("=" * 60)
            
            # Sugerir acciones prioritarias
            if any(a['tipo'] == 'DISCREPANCIA_TABLAS' for a in alertas):
                print("1. 🚨 URGENTE: Ejecutar 'python scripts/sync_osce_risk_daily.py'")
            if any(a['tipo'] == 'VENCIDAS_NO_ACTUALIZADAS' for a in alertas):
                print("2. ⚠️  Ejecutar sincronización para auto-corregir estados")
            if any(a['tipo'] == 'VENCIDAS_RECIENTES' for a in alertas):
                print("3. 📋 Revisar si hay resoluciones judiciales recientes")
            if any(a['tipo'] == 'FECHAS_FALTANTES' for a in alertas):
                print("4. 🔍 Investigar sanciones con fechas faltantes")
            
            return len(alertas) == 0  # True si no hay alertas
            
    except Exception as e:
        print(f"❌ Error en auditoría: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = auditar_sanciones()
    sys.exit(0 if success else 1)
