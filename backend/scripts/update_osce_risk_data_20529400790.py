#!/usr/bin/env python3
"""
Actualizar tabla agregada osce_risk_data para RUC 20529400790
Después de actualizar osce_sanciones_detalle
"""

import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get('DATABASE_URL')

def update_osce_risk_data():
    if not DB_URL:
        print("❌ DATABASE_URL no configurada")
        return False
    
    engine = create_engine(DB_URL)
    
    with engine.connect() as conn:
        # Verificar datos actuales
        result = conn.execute(
            text("SELECT * FROM osce_risk_data WHERE ruc = :ruc"),
            {'ruc': '20529400790'}
        ).fetchone()
        
        if not result:
            print("⚠️ No se encontró en osce_risk_data")
            return False
        
        print("📊 Datos actuales en osce_risk_data:")
        print(f"   RUC: {result.ruc}")
        print(f"   Sanciones vigentes: {result.sanciones_vigentes}")
        print(f"   Inhabilitaciones vigentes: {result.inhabilitaciones_vigentes}")
        print(f"   Días inhabilitación restantes: {result.dias_inhabilitacion_restantes}")
        print(f"   Cantidad sanciones: {result.cantidad_sanciones}")
        print(f"   Score OSCE anual: {result.score_osce_anual}")
        
        # Actualizar: ya no tiene sanciones vigentes
        conn.execute(
            text("""
                UPDATE osce_risk_data 
                SET sanciones_vigentes = 0,
                    inhabilitaciones_vigentes = 0,
                    dias_inhabilitacion_restantes = 0,
                    score_osce_anual = 95.0,
                    fecha_sync = NOW()
                WHERE ruc = :ruc
            """),
            {'ruc': '20529400790'}
        )
        conn.commit()
        
        print("\n✅ Actualizado:")
        print("   Sanciones vigentes: 0")
        print("   Inhabilitaciones vigentes: 0")
        print("   Días restantes: 0")
        print("   Score OSCE: 95.0")
        
        return True

if __name__ == '__main__':
    update_osce_risk_data()
