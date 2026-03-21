#!/bin/bash
# Script de deploy del frontend a Netlify

echo "🚀 Deploy de Conflict Zero a Netlify"
echo "====================================="
echo ""

# Verificar si estamos en el directorio correcto
if [ ! -f "package.json" ]; then
    echo "❌ Error: No se encontró package.json"
    echo "Ejecuta este script desde la carpeta frontend/"
    exit 1
fi

echo "📦 Instalando dependencias..."
npm install

echo ""
echo "🔧 Verificando configuración..."

# Verificar netlify.toml
if [ ! -f "netlify.toml" ]; then
    echo "⚠️  Creando netlify.toml..."
    cat > netlify.toml << 'EOF'
[build]
  command = "npm run build"
  publish = "out"

[build.environment]
  NEXT_PUBLIC_API_URL = "https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod"

[[redirects]]
  from = "/api/*"
  to = "https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod/:splat"
  status = 200
EOF
    echo "✅ netlify.toml creado"
fi

echo "✅ Configuración lista"

echo ""
echo "🏗️  Construyendo proyecto..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Error en el build"
    exit 1
fi

echo ""
echo "✅ Build completado exitosamente!"
echo ""
echo "📁 Archivos generados en: ./out/"
echo ""

# Verificar si Netlify CLI está instalado
if command -v netlify &> /dev/null; then
    echo "🚀 Netlify CLI detectado"
    echo ""
    echo "Para deployar ejecuta:"
    echo "  netlify deploy --prod --dir=out"
    echo ""
    echo "O si es primera vez:"
    echo "  netlify init"
    echo "  netlify deploy --prod --dir=out"
else
    echo "⚠️  Netlify CLI no instalado"
    echo ""
    echo "Para instalar: npm install -g netlify-cli"
    echo ""
    echo "O sube manualmente la carpeta 'out/' a Netlify:"
    echo "  1. Ve a https://app.netlify.com/drop"
    echo "  2. Arrastra la carpeta 'out/'"
    echo "  3. Listo!"
fi

echo ""
echo "🧪 Después del deploy, prueba:"
echo "  curl https://tu-dominio.netlify.app/api/consulta-osce/20100017491"
echo ""
