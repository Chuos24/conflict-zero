#!/bin/bash
# Setup script para crear servicio en Render via Blueprint

set -e

# Crear blueprint con render.yaml
RENDER_KEY="rnd_t7RndlkxC4kMflvPuXYfqgeVpcHP"
OWNER_ID="tea-d6v080vfte5s73digi30"

echo "🚀 Creando servicio conflict-zero-api en Render..."

# Crear servicio usando el repo directamente
curl -s -X POST \
    -H "Authorization: Bearer $RENDER_KEY" \
    -H "Content-Type: application/json" \
    -d "{
        \"type\": \"web_service\",
        \"name\": \"conflict-zero-api\",
        \"ownerId\": \"$OWNER_ID\",
        \"repo\": \"https://github.com/Chuos24/conflict-zero\",
        \"branch\": \"main\",
        \"autoDeploy\": \"yes\",
        \"serviceDetails\": {
            \"buildCommand\": \"pip install -r requirements.txt\",
            \"startCommand\": \"uvicorn app.main:app --host 0.0.0.0 --port \\$PORT\",
            \"env\": \"python\",
            \"envSpecificDetails\": {
                \"runtime\": \"python\"
            }
        }
    }" \
    "https://api.render.com/v1/services" | jq -r '.id // .message'
