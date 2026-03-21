#!/bin/bash
# Script para iniciar el backend de Conflict Zero

cd "$(dirname "$0")"

# Verificar si hay un servidor corriendo
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Ya hay un servidor corriendo en el puerto 8000"
    echo "   Matando proceso anterior..."
    pkill -f uvicorn
    sleep 2
fi

# Eliminar base de datos anterior si existe (para desarrollo)
if [ -f "conflictzero.db" ]; then
    echo "🗑️  Eliminando base de datos anterior..."
    rm conflictzero.db
fi

echo "🚀 Iniciando Conflict Zero API..."
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

# Iniciar servidor
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
