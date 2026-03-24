#!/bin/bash
# PostgreSQL Migration Script for Conflict Zero
# Uso: ./migrate-to-postgres.sh

set -e  # Exit on error

echo "🚀 Conflict Zero - PostgreSQL Migration"
echo "========================================"
echo ""

# Configuración
BACKUP_DIR="./backups/postgres-migration-$(date +%Y%m%d-%H%M%S)"
SQLITE_DB="./conflictzero.db"

echo "📁 Creando directorio de backup: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

echo ""
echo "📊 PASO 1: Analizando base de datos SQLite actual"
echo "---------------------------------------------------"

# Verificar si existe SQLite
if [ ! -f "$SQLITE_DB" ]; then
    echo "❌ No se encontró $SQLITE_DB"
    exit 1
fi

echo "✅ Base de datos SQLite encontrada"
echo "📏 Tamaño: $(du -h $SQLITE_DB | cut -f1)"

# Contar registros por tabla
echo ""
echo "📈 Registros por tabla:"
python3 << 'PYTHON_CODE'
import sqlite3
import json

try:
    conn = sqlite3.connect('conflictzero.db')
    cursor = conn.cursor()
    
    tables = ['users', 'verification_requests', 'api_keys', 'system_logs']
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  - {table}: {count} registros")
        except:
            print(f"  - {table}: 0 registros (tabla no existe)")
    
    conn.close()
except Exception as e:
    print(f"Error leyendo SQLite: {e}")
PYTHON_CODE

echo ""
echo "💾 PASO 2: Exportando datos a JSON"
echo "-------------------------------------"

python3 << 'PYTHON_CODE'
import sqlite3
import json
from datetime import datetime

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

try:
    conn = sqlite3.connect('conflictzero.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Exportar users
    cursor.execute("SELECT * FROM users")
    users = [dict(row) for row in cursor.fetchall()]
    with open('backups/postgres-migration-*/users.json', 'w') as f:
        json.dump(users, f, default=serialize_datetime, indent=2)
    print(f"✅ Usuarios exportados: {len(users)}")
    
    # Exportar verification_requests
    cursor.execute("SELECT * FROM verification_requests")
    requests = [dict(row) for row in cursor.fetchall()]
    with open('backups/postgres-migration-*/verification_requests.json', 'w') as f:
        json.dump(requests, f, default=serialize_datetime, indent=2)
    print(f"✅ Verificaciones exportadas: {len(requests)}")
    
    # Exportar api_keys
    cursor.execute("SELECT * FROM api_keys")
    keys = [dict(row) for row in cursor.fetchall()]
    with open('backups/postgres-migration-*/api_keys.json', 'w') as f:
        json.dump(keys, f, default=serialize_datetime, indent=2)
    print(f"✅ API Keys exportadas: {len(keys)}")
    
    conn.close()
    print("✅ Exportación completada")
    
except Exception as e:
    print(f"❌ Error exportando: {e}")
    import traceback
    traceback.print_exc()
PYTHON_CODE

echo ""
echo "📋 PASO 3: Generando SQL para PostgreSQL"
echo "-----------------------------------------"

cat > "$BACKUP_DIR/create_tables.sql" << 'SQL'
-- PostgreSQL Schema for Conflict Zero
-- Compatible con SQLAlchemy models

-- Extensión para UUID (si se desea migrar a UUID nativo en el futuro)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabla users
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    ruc VARCHAR(11),
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    plan_type VARCHAR(50) DEFAULT 'essential',
    api_key VARCHAR(255) UNIQUE,
    monthly_requests INTEGER DEFAULT 0,
    monthly_limit INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_api_key ON users(api_key);

-- Tabla verification_requests
CREATE TABLE IF NOT EXISTS verification_requests (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ruc VARCHAR(11) NOT NULL,
    company_name VARCHAR(255),
    score INTEGER NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    sunat_debt FLOAT DEFAULT 0.0,
    sunat_score_contribution FLOAT DEFAULT 0.0,
    osce_sanctions_count INTEGER DEFAULT 0,
    osce_score_contribution FLOAT DEFAULT 0.0,
    osce_sanctions_details JSONB DEFAULT '[]'::jsonb,
    tce_sanctions_count INTEGER DEFAULT 0,
    tce_score_contribution FLOAT DEFAULT 0.0,
    tce_sanctions_details JSONB DEFAULT '[]'::jsonb,
    ml_anomaly_score FLOAT DEFAULT 0.0,
    ml_score_contribution FLOAT DEFAULT 0.0,
    raw_data JSONB DEFAULT '{}'::jsonb,
    pdf_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_verification_requests_user_id ON verification_requests(user_id);
CREATE INDEX idx_verification_requests_ruc ON verification_requests(ruc);
CREATE INDEX idx_verification_requests_created_at ON verification_requests(created_at);

-- Tabla api_keys
CREATE TABLE IF NOT EXISTS api_keys (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    last_used_at TIMESTAMP,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

-- Tabla system_logs
CREATE TABLE IF NOT EXISTS system_logs (
    id VARCHAR(36) PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    source VARCHAR(100),
    meta_data JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_logs_created_at ON system_logs(created_at);
CREATE INDEX idx_system_logs_level ON system_logs(level);

-- Trigger para actualizar updated_at en users
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at 
    BEFORE UPDATE ON users 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Comentarios para documentación
COMMENT ON TABLE users IS 'Usuarios registrados en la plataforma';
COMMENT ON TABLE verification_requests IS 'Historial de verificaciones de RUC';
COMMENT ON TABLE api_keys IS 'API keys para integraciones';
COMMENT ON TABLE system_logs IS 'Logs del sistema';
SQL

echo "✅ Script SQL generado: $BACKUP_DIR/create_tables.sql"

echo ""
echo "📝 PASO 4: Instrucciones para completar la migración"
echo "----------------------------------------------------"
cat << 'INSTRUCTIONS'

PRÓXIMOS PASOS MANUALES:

1. CREAR POSTGRESQL EN RENDER:
   - Ir a https://dashboard.render.com
   - Click "New" → "PostgreSQL"
   - Nombre: conflict-zero-db
   - Plan: Free (o Starter $7/mes para producción)
   - Esperar a que esté "Available" (2-3 minutos)

2. OBTENER CREDENCIALES:
   - En el dashboard de la DB, copiar "External Database URL"
   - O usar "Internal Database URL" si backend está en mismo region

3. CONECTARSE A POSTGRESQL:
   psql $DATABASE_URL
   
   # O usar pgAdmin, DBeaver, etc.

4. CREAR TABLAS:
   \i backups/postgres-migration-XXXX/create_tables.sql

5. MIGRAR DATOS (usaré script Python):
   python3 import_to_postgres.py

6. ACTUALIZAR VARIABLES DE ENTORNO EN RENDER:
   - DATABASE_URL: (la URL de PostgreSQL)
   - Redeploy del servicio

7. VERIFICAR:
   - Health check: GET /health
   - Login funciona
   - Datos presentes

INSTRUCTIONS

echo ""
echo "✅ Script de migración preparado en: $BACKUP_DIR"
echo ""
echo "🎯 Para continuar, ejecuta este script y sigue las instrucciones"
