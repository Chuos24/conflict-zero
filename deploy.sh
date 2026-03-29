#!/bin/bash
# Deploy script for Conflict Zero API
# Uso: ./deploy.sh "mensaje del commit"

set -e

# Configuración
REPO="Chuos24/conflict-zero"
FILE="backend/api_v3.py"
TOKEN="${GITHUB_TOKEN:-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}"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Validar mensaje
if [ -z "$1" ]; then
    echo -e "${RED}Error:${NC} Mensaje de commit requerido"
    echo "Uso: ./deploy.sh \"mensaje del commit\""
    exit 1
fi

MESSAGE="$1"

echo -e "${YELLOW}🚀 Deploy de Conflict Zero API${NC}"
echo "================================"
echo ""

# Verificar archivo existe
if [ ! -f "backend/api_v3.py" ]; then
    echo -e "${RED}Error:${NC} No se encuentra backend/api_v3.py"
    exit 1
fi

# Obtener SHA actual del archivo
echo -n "📡 Obteniendo SHA actual... "
SHA=$(curl -s -H "Authorization: token $TOKEN" \
    "https://api.github.com/repos/$REPO/contents/$FILE?ref=main" | jq -r '.sha')

if [ "$SHA" = "null" ] || [ -z "$SHA" ]; then
    echo -e "${RED}Error${NC}"
    echo "No se pudo obtener SHA. Verifica el token."
    exit 1
fi
echo -e "${GREEN}OK${NC} ($SHA)"

# Codificar contenido
echo -n "📦 Codificando archivo... "
CONTENT=$(base64 -w0 backend/api_v3.py)
echo -e "${GREEN}OK${NC}"

# Crear commit
echo -n "📝 Subiendo a GitHub... "
RESPONSE=$(curl -s -X PUT -H "Authorization: token $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"message\":\"$MESSAGE\",\"content\":\"$CONTENT\",\"sha\":\"$SHA\"}" \
    "https://api.github.com/repos/$REPO/contents/$FILE")

COMMIT_SHA=$(echo "$RESPONSE" | jq -r '.commit.sha')

if [ "$COMMIT_SHA" = "null" ] || [ -z "$COMMIT_SHA" ]; then
    echo -e "${RED}Error${NC}"
    echo "Respuesta: $RESPONSE"
    exit 1
fi
echo -e "${GREEN}OK${NC}"
echo "   Commit: ${COMMIT_SHA:0:8}"
echo "   Mensaje: $MESSAGE"
echo ""

# Esperar deploy en Render
echo -e "${YELLOW}⏳ Esperando deploy en Render...${NC}"
echo "   Esto toma ~60-90 segundos"
echo ""

RENDER_KEY="${RENDER_API_KEY:-rnd_TD2zaOUFhKiLOcvk5qQJNqxqAMKE}"
export RENDER_API_KEY="$RENDER_KEY"

for i in {1..20}; do
    STATUS=$(render deploys list srv-d6vagtfafjfc73cu0kdg --output json 2>/dev/null | \
        jq -r '.[0].status' 2>/dev/null || echo "unknown")
    
    printf "\r   [%2d/20] Status: %-15s" "$i" "$STATUS"
    
    if [ "$STATUS" = "live" ]; then
        echo ""
        echo ""
        echo -e "${GREEN}✅ Deploy completado!${NC}"
        echo ""
        echo "URLs:"
        echo "   API:     https://conflict-zero-api.onrender.com"
        echo "   Health:  https://conflict-zero-api.onrender.com/api/v3/health"
        exit 0
    fi
    
    sleep 6
done

echo ""
echo ""
echo -e "${YELLOW}⚠️  Timeout esperando deploy${NC}"
echo "   Verifica manualmente: https://dashboard.render.com"
exit 0
