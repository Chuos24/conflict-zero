#!/bin/bash
# Script para preparar el repositorio de Conflict Zero

echo "🚀 Preparando Conflict Zero para GitHub..."
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: No se encuentran carpetas backend/ o frontend/"
    echo "   Ejecuta este script desde la raíz del proyecto"
    exit 1
fi

# Crear archivo .gitignore
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
*.env
.venv
pip-log.txt

# Database
*.db
*.sqlite3

# Next.js
frontend/node_modules/
frontend/.next/
frontend/out/
frontend/.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Build outputs
*.zip
dist/
build/

# Secrets
.env
!.env.example
EOF

echo "✅ Archivo .gitignore creado"

# Verificar estructura
echo ""
echo "📁 Estructura del proyecto:"
find . -maxdepth 2 -type f -name "*.py" -o -name "*.tsx" -o -name "*.ts" -o -name "*.json" -o -name "*.md" | grep -v node_modules | grep -v __pycache__ | sort | head -30

echo ""
echo "═══════════════════════════════════════════════"
echo "✅ TODO LISTO PARA SUBIR A GITHUB"
echo "═══════════════════════════════════════════════"
echo ""
echo "📋 PASOS A SEGUIR:"
echo ""
echo "1. Crea un nuevo repositorio en GitHub:"
echo "   https://github.com/new"
echo "   Nombre: conflict-zero"
echo "   Público o Privado (tú eliges)"
echo ""
echo "2. En tu terminal, ejecuta:"
echo ""
echo "   git init"
echo "   git add ."
echo "   git commit -m 'Initial commit'"
echo "   git branch -M main"
echo "   git remote add origin https://github.com/Chuos24/conflict-zero.git"
echo "   git push -u origin main"
echo ""
echo "3. Ve a Render.com y deploya:"
echo "   https://render.com"
echo "   New Web Service → Connect GitHub → Selecciona repo"
echo ""
echo "4. Configura variables de entorno en Render:"
echo "   PERU_API_KEY = d02bb5a71984e759885a4e47a575715c"
echo ""
echo "5. Deploya frontend a Netlify con el ZIP"
echo ""
echo "═══════════════════════════════════════════════"
echo ""
