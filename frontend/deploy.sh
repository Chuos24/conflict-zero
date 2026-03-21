#!/bin/bash
# Script de deploy del frontend a Vercel

echo "🚀 Deploy de Conflict Zero Frontend"
echo "===================================="
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
echo "🔧 Configurando variables de entorno..."
echo "NEXT_PUBLIC_API_URL=https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod" > .env.local
echo "NEXT_PUBLIC_BACKEND_URL=${BACKEND_URL:-http://localhost:8000}" >> .env.local
echo "✅ Variables configuradas"

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

# Verificar si Vercel CLI está instalado
if command -v vercel &> /dev/null; then
    echo "🚀 Vercel CLI detectado"
    echo "¿Deseas deployar ahora? (s/n)"
    read -r response
    
    if [ "$response" = "s" ] || [ "$response" = "S" ]; then
        echo "Deployando a Vercel..."
        vercel --prod
    else
        echo ""
        echo "Para deployar manualmente ejecuta:"
        echo "  vercel --prod"
        echo ""
        echo "O sube la carpeta 'out/' a tu hosting preferido"
    fi
else
    echo "⚠️  Vercel CLI no instalado"
    echo ""
    echo "Para instalar: npm i -g vercel"
    echo ""
    echo "O sube manualmente la carpeta 'out/' a:"
    echo "  - Vercel (drag & drop en vercel.com)"
    echo "  - Netlify"
    echo "  - AWS S3"
    echo "  - Cualquier hosting estático"
fi

echo ""
echo "🧪 Prueba después del deploy:"
echo "  curl https://tu-dominio.vercel.app/api/consulta-osce/20100017491"
echo ""
