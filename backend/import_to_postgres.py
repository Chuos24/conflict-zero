#!/usr/bin/env python3
"""
Script para importar datos de SQLite (exportados a JSON) a PostgreSQL
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import Json
from psycopg2.extensions import register_adapter

# Registrar adapter para dict -> JSON
register_adapter(dict, Json)

def get_connection():
    """Obtener conexión a PostgreSQL desde variable de entorno"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL no está configurada")
        print("💡 Ejemplo: export DATABASE_URL='postgresql://user:pass@host:5432/db'")
        sys.exit(1)
    
    return psycopg2.connect(database_url)

def import_users(cursor, data):
    """Importar usuarios"""
    if not data:
        print("⚠️ No hay usuarios para importar")
        return
    
    query = """
    INSERT INTO users (
        id, email, hashed_password, full_name, company_name, ruc,
        is_active, is_admin, plan_type, api_key, monthly_requests, monthly_limit,
        created_at, updated_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO UPDATE SET
        email = EXCLUDED.email,
        hashed_password = EXCLUDED.hashed_password,
        full_name = EXCLUDED.full_name,
        updated_at = EXCLUDED.updated_at
    """
    
    count = 0
    for user in data:
        try:
            cursor.execute(query, (
                user.get('id'),
                user.get('email'),
                user.get('hashed_password'),
                user.get('full_name'),
                user.get('company_name'),
                user.get('ruc'),
                user.get('is_active', True),
                user.get('is_admin', False),
                user.get('plan_type', 'essential'),
                user.get('api_key'),
                user.get('monthly_requests', 0),
                user.get('monthly_limit', 1000),
                user.get('created_at'),
                user.get('updated_at')
            ))
            count += 1
        except Exception as e:
            print(f"  ⚠️ Error importando usuario {user.get('email')}: {e}")
    
    print(f"✅ Usuarios importados: {count}")

def import_verification_requests(cursor, data):
    """Importar solicitudes de verificación"""
    if not data:
        print("⚠️ No hay verificaciones para importar")
        return
    
    query = """
    INSERT INTO verification_requests (
        id, user_id, ruc, company_name, score, risk_level,
        sunat_debt, sunat_score_contribution,
        osce_sanctions_count, osce_score_contribution, osce_sanctions_details,
        tce_sanctions_count, tce_score_contribution, tce_sanctions_details,
        ml_anomaly_score, ml_score_contribution,
        raw_data, pdf_url, created_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    """
    
    count = 0
    for req in data:
        try:
            cursor.execute(query, (
                req.get('id'),
                req.get('user_id'),
                req.get('ruc'),
                req.get('company_name'),
                req.get('score'),
                req.get('risk_level'),
                req.get('sunat_debt', 0.0),
                req.get('sunat_score_contribution', 0.0),
                req.get('osce_sanctions_count', 0),
                req.get('osce_score_contribution', 0.0),
                Json(req.get('osce_sanctions_details', [])),
                req.get('tce_sanctions_count', 0),
                req.get('tce_score_contribution', 0.0),
                Json(req.get('tce_sanctions_details', [])),
                req.get('ml_anomaly_score', 0.0),
                req.get('ml_score_contribution', 0.0),
                Json(req.get('raw_data', {})),
                req.get('pdf_url'),
                req.get('created_at')
            ))
            count += 1
        except Exception as e:
            print(f"  ⚠️ Error importando verificación {req.get('id')}: {e}")
    
    print(f"✅ Verificaciones importadas: {count}")

def import_api_keys(cursor, data):
    """Importar API keys"""
    if not data:
        print("⚠️ No hay API keys para importar")
        return
    
    query = """
    INSERT INTO api_keys (
        id, user_id, key_hash, name, is_active, last_used_at, usage_count, created_at, expires_at
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    """
    
    count = 0
    for key in data:
        try:
            cursor.execute(query, (
                key.get('id'),
                key.get('user_id'),
                key.get('key_hash'),
                key.get('name'),
                key.get('is_active', True),
                key.get('last_used_at'),
                key.get('usage_count', 0),
                key.get('created_at'),
                key.get('expires_at')
            ))
            count += 1
        except Exception as e:
            print(f"  ⚠️ Error importando API key {key.get('id')}: {e}")
    
    print(f"✅ API keys importadas: {count}")

def main():
    print("🚀 Importando datos a PostgreSQL")
    print("=" * 50)
    
    # Buscar archivos JSON en directorios de backup
    backup_dirs = sorted(Path('./backups').glob('postgres-migration-*'))
    if not backup_dirs:
        print("❌ No se encontraron directorios de backup")
        print("💡 Ejecuta primero: ./migrate-to-postgres.sh")
        sys.exit(1)
    
    backup_dir = backup_dirs[-1]  # Usar el más reciente
    print(f"📁 Usando backup: {backup_dir}")
    
    # Cargar datos JSON
    data_files = {
        'users': backup_dir / 'users.json',
        'verification_requests': backup_dir / 'verification_requests.json',
        'api_keys': backup_dir / 'api_keys.json'
    }
    
    data = {}
    for name, filepath in data_files.items():
        if filepath.exists():
            with open(filepath) as f:
                data[name] = json.load(f)
                print(f"✅ {name}: {len(data[name])} registros cargados")
        else:
            print(f"⚠️ {name}: archivo no encontrado")
            data[name] = []
    
    # Conectar a PostgreSQL
    print("\n🔗 Conectando a PostgreSQL...")
    try:
        conn = get_connection()
        cursor = conn.cursor()
        print("✅ Conexión exitosa")
    except Exception as e:
        print(f"❌ Error conectando: {e}")
        sys.exit(1)
    
    # Importar datos
    print("\n📥 Importando datos...")
    
    try:
        import_users(cursor, data.get('users', []))
        import_verification_requests(cursor, data.get('verification_requests', []))
        import_api_keys(cursor, data.get('api_keys', []))
        
        conn.commit()
        print("\n✅ Importación completada exitosamente")
        
        # Verificación final
        print("\n📊 Verificación:")
        cursor.execute("SELECT COUNT(*) FROM users")
        print(f"  - Usuarios en PostgreSQL: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM verification_requests")
        print(f"  - Verificaciones en PostgreSQL: {cursor.fetchone()[0]}")
        
        cursor.execute("SELECT COUNT(*) FROM api_keys")
        print(f"  - API Keys en PostgreSQL: {cursor.fetchone()[0]}")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante importación: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
    
    print("\n🎉 Migración completada!")
    print("\nPróximo paso: Actualizar DATABASE_URL en Render y redeploy")

if __name__ == '__main__':
    main()
