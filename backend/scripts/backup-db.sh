#!/bin/bash
# Script de backup para PostgreSQL en Render
# Uso: ./backup-db.sh [DATABASE_URL]

set -e

DB_URL="${1:-$DATABASE_URL}"

if [ -z "$DB_URL" ]; then
    echo "Error: No se proporcionó DATABASE_URL"
    echo "Uso: ./backup-db.sh 'postgresql://user:pass@host:port/dbname'"
    exit 1
fi

# Extraer componentes de la URL
# postgresql://user:password@host:port/dbname
DB_USER=$(echo "$DB_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo "$DB_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_HOST=$(echo "$DB_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
DB_PORT=$(echo "$DB_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
DB_NAME=$(echo "$DB_URL" | sed -n 's/.*\/[0-9]*\/\(.*\)/\1/p')

# Si no se pudo extraer el puerto, usar 5432 por defecto
if [ -z "$DB_PORT" ]; then
    DB_PORT=5432
fi

# Fecha para el nombre del archivo
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backup_${DB_NAME}_${BACKUP_DATE}.sql"

echo "=========================================="
echo "Backup de Base de Datos PostgreSQL"
echo "=========================================="
echo "Host: $DB_HOST"
echo "Base de datos: $DB_NAME"
echo "Fecha: $BACKUP_DATE"
echo "Archivo: $BACKUP_FILE"
echo "=========================================="

# Crear backup
export PGPASSWORD="$DB_PASS"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --verbose \
    --no-owner \
    --no-acl \
    --format=plain \
    > "$BACKUP_FILE"

echo ""
echo "✓ Backup completado: $BACKUP_FILE"
echo "Tamaño: $(du -h "$BACKUP_FILE" | cut -f1)"

# Crear también versión comprimida
gzip -k "$BACKUP_FILE"
echo "✓ Backup comprimido: ${BACKUP_FILE}.gz"
echo "Tamaño comprimido: $(du -h "${BACKUP_FILE}.gz" | cut -f1)"

unset PGPASSWORD
