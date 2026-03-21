#!/bin/bash
# Script para actualizar la URL del backend en el frontend

if [ -z "$1" ]; then
    echo "❌ Uso: ./update-backend-url.sh https://tu-api.render.com"
    exit 1
fi

BACKEND_URL=$1

echo "🔄 Actualizando backend URL a: $BACKEND_URL"

# Reemplazar en todos los archivos JS
cd frontend/out

# Buscar y reemplazar localhost:8000
find . -type f \( -name "*.js" -o -name "*.html" \) -exec sed -i "s|http://localhost:8000|$BACKEND_URL|g" {} \;

echo "✅ URL actualizada en archivos estáticos"

# Recrear el ZIP
cd ..
rm -f conflict-zero-static.zip
cd out
zip -r ../conflict-zero-static.zip . 2>/dev/null

cd ..
echo ""
echo "✅ Nuevo ZIP creado: conflict-zero-static.zip"
echo "📦 Listo para subir a Netlify"
