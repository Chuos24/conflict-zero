#!/bin/bash
# Script para deployar el backend Python en Render

echo "═══════════════════════════════════════════════════════════"
echo "🚀 DEPLOY AUTOMATICO - Conflict Zero Backend Python"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Verificar si Render CLI esta instalado
if ! command -v render &> /dev/null; then
    echo "⚠️  Render CLI no instalado. Instalando..."
    curl -fsSL https://raw.githubusercontent.com/render-oss/render-cli/main/install.sh | bash
fi

echo "📋 Estado actual:"
echo "   - Repo: https://github.com/Chuos24/conflict-zero"
echo "   - Branch: main"
echo "   - Directorio: backend/"
echo ""

echo "🔧 Configuracion del servicio:"
echo "   - Nombre: conflictzero-backend-new"
echo "   - Runtime: Python 3.11"
echo "   - Build: pip install -r requirements.txt"
echo "   - Start: uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
echo ""

echo "📦 Variables de entorno necesarias:"
echo "   - DATABASE_URL (auto-generada por Render)"
echo "   - SECRET_KEY (auto-generada)"
echo "   - PERU_API_KEY=d02bb5a71984e759885a4e47a575715c"
echo "   - ENVIRONMENT=production"
echo ""

echo "═══════════════════════════════════════════════════════════"
echo ""
echo "Para deployar automaticamente:"
echo ""
echo "1. Ve a: https://dashboard.render.com/select-repo?type=web"
echo ""
echo "2. Selecciona: 'conflict-zero'"
echo ""
echo "3. Configura:"
echo "   Name: conflictzero-backend-new"
echo "   Region: Oregon (US West)"
echo "   Branch: main"
echo "   Root Directory: backend"
echo "   Runtime: Python 3"
echo "   Build Command: pip install -r requirements.txt"
echo "   Start Command: uvicorn app.main:app --host 0.0.0.0 --port \$PORT"
echo ""
echo "4. Environment Variables:"
echo "   PERU_API_KEY = d02bb5a71984e759885a4e47a575715c"
echo "   ENVIRONMENT = production"
echo "   ALLOWED_HOSTS = *"
echo ""
echo "5. Click 'Create Web Service'"
echo ""
echo "La URL sera algo como:"
echo "   https://conflictzero-backend-new.onrender.com"
echo ""
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "⏳ Despues del deploy, actualizare el frontend automaticamente."
echo ""

# Guardar estado para automatizacion posterior
mkdir -p /tmp/render-deploy
echo "pending" > /tmp/render-deploy/status.txt
echo "conflictzero-backend-new" > /tmp/render-deploy/service_name.txt