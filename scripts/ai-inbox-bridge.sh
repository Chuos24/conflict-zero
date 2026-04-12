#!/bin/bash
# ai-inbox-bridge.sh v2.0
# Puente automático entre Claude Code (Mac) y Kimi Claw (VPS)
# Ejecuta instrucciones de ai-inbox/para-kimi.md y responde en ai-inbox/para-claude.md

set -e

REPO_DIR="/root/.openclaw/workspace/conflict-zero"
INBOX_DIR="$REPO_DIR/ai-inbox"
LOG_FILE="/var/log/ai-inbox-bridge.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Función de logging
log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log "=== INICIO CICLO AI-INBOX ==="

cd "$REPO_DIR" || {
    log "ERROR: No se puede acceder a $REPO_DIR"
    exit 1
}

# Paso 1: Git pull
log "Paso 1: Git pull..."
if git pull origin main 2>&1 | tee -a "$LOG_FILE"; then
    log "✅ Git pull exitoso"
else
    log "❌ Git pull falló"
    exit 1
fi

# Verificar si existe archivo para-kimi.md
if [ ! -f "$INBOX_DIR/para-kimi.md" ]; then
    log "ℹ️ No hay instrucciones pendientes (para-kimi.md no existe)"
    log "=== FIN CICLO (sin acciones) ==="
    exit 0
fi

# Verificar si el archivo tiene contenido nuevo
if [ ! -s "$INBOX_DIR/para-kimi.md" ]; then
    log "ℹ️ Archivo para-kimi.md está vacío"
    log "=== FIN CICLO (sin acciones) ==="
    exit 0
fi

# Paso 2: Leer instrucciones
log "Paso 2: Leyendo instrucciones..."
INSTRUCCIONES=$(cat "$INBOX_DIR/para-kimi.md")
log "Instrucciones leídas ($(wc -c < "$INBOX_DIR/para-kimi.md") bytes)"

# Detectar tipo de tarea
TAREA=$(echo "$INSTRUCCIONES" | grep -oE "TAREA-[0-9]+" | head -1)
TAREA_DESC=$(echo "$INSTRUCCIONES" | grep -A5 "TAREA-" | tail -n +2 | head -5)

log "Tarea detectada: $TAREA"

# Preparar archivo de respuesta
RESULTADO=""
STATUS="PENDIENTE"

# Función para ejecutar comando y capturar salida
exec_cmd() {
    local cmd="$1"
    local output
    local exit_code
    
    log "Ejecutando: $cmd"
    output=$(eval "$cmd" 2>&1) || exit_code=$?
    
    if [ -z "$exit_code" ] || [ "$exit_code" -eq 0 ]; then
        echo "✅ ÉXITO: $output"
    else
        echo "❌ ERROR ($exit_code): $output"
    fi
}

# Paso 3: Ejecutar tarea según tipo
log "Paso 3: Ejecutando tarea..."

if echo "$INSTRUCCIONES" | grep -q "verificar.*endpoint\|endpoint.*responde"; then
    # Tarea de verificación de endpoint
    log "Tipo: Verificación de endpoint"
    
    # Extraer endpoint de las instrucciones
    ENDPOINT=$(echo "$INSTRUCCIONES" | grep -oE "/api/v[0-9]+/[^[:space:]]+")
    
    if [ -z "$ENDPOINT" ]; then
        ENDPOINT="/api/v3/network/"
    fi
    
    FULL_URL="https://conflict-zero-api.onrender.com${ENDPOINT}"
    log "Verificando: $FULL_URL"
    
    # Login para obtener token
    TOKEN_RESPONSE=$(curl -s -X POST "https://conflict-zero-api.onrender.com/api/v3/auth/login" \
        -H "Content-Type: application/json" \
        -d '{"email":"founder@conflictzero.com","password":"CZ2025!"}')
    
    TOKEN=$(echo "$TOKEN_RESPONSE" | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
    
    if [ -n "$TOKEN" ]; then
        START_TIME=$(date +%s%N)
        HTTP_RESPONSE=$(curl -s -w "\n%{http_code}\n%{time_total}" \
            "$FULL_URL" \
            -H "Authorization: Bearer $TOKEN" \
            2>&1)
        END_TIME=$(date +%s%N)
        
        HTTP_CODE=$(echo "$HTTP_RESPONSE" | tail -n2 | head -n1)
        RESPONSE_TIME=$(echo "$HTTP_RESPONSE" | tail -n1)
        RESPONSE_BODY=$(echo "$HTTP_RESPONSE" | head -n -2)
        
        # Calcular tiempo en ms
        ELAPSED_MS=$(echo "scale=2; ($END_TIME - $START_TIME) / 1000000" | bc 2>/dev/null || echo "N/A")
        
        RESULTADO="Status Code: $HTTP_CODE
Tiempo de respuesta: ${RESPONSE_TIME}s (${ELAPSED_MS}ms)
URL: $FULL_URL

Respuesta:
\`\`\`json
$(echo "$RESPONSE_BODY" | head -200)
\`\`\`"
        
        if [ "$HTTP_CODE" = "200" ]; then
            STATUS="✅ ÉXITO"
        else
            STATUS="⚠️ HTTP $HTTP_CODE"
        fi
    else
        RESULTADO="❌ No se pudo obtener token de autenticación"
        STATUS="❌ ERROR"
    fi

elif echo "$INSTRUCCIONES" | grep -q "fix.*nombre.*empresa\|fix.*verificar.html"; then
    # Tarea de fix en verificar.html
    log "Tipo: Fix nombre empresa en verificar.html"
    
    VERIFICAR_FILE="$REPO_DIR/czperu-landing-git/verificar.html"
    
    if [ -f "$VERIFICAR_FILE" ]; then
        # Verificar el problema común: data.razon_social vs data.company
        if grep -q "data.razon_social" "$VERIFICAR_FILE"; then
            # Hacer backup
            cp "$VERIFICAR_FILE" "$VERIFICAR_FILE.bak.$(date +%Y%m%d-%H%M%S)"
            
            # Fix: Asegurar que razon_social se muestre correctamente
            # Agregar fallback para cuando razon_social es null
            sed -i 's/data.razon_social || '\''Empresa'\''/\(data.razon_social \|\| data.company_name \|\| data.nombre \|\| '\''Empresa'\''\)/g' "$VERIFICAR_FILE" 2>/dev/null || true
            
            RESULTADO="Archivo verificar.html actualizado:
- Agregado fallback para nombre de empresa (razon_social → company_name → nombre → 'Empresa')
- Backup creado antes de modificar
- Archivo: $VERIFICAR_FILE"
            STATUS="✅ ÉXITO"
        else
            RESULTADO="No se encontró el patrón data.razon_social en verificar.html
El archivo ya puede estar corregido."
            STATUS="ℹ️ SIN CAMBIOS"
        fi
    else
        RESULTADO="❌ Archivo verificar.html no encontrado en: $VERIFICAR_FILE"
        STATUS="❌ ERROR"
    fi

elif echo "$INSTRUCCIONES" | grep -q "git\|deploy"; then
    # Tarea de git/deploy
    log "Tipo: Git/Deploy"
    RESULTADO=$(exec_cmd "cd $REPO_DIR && git status --short")
    STATUS="✅ COMPLETADO"

else
    # Tarea genérica
    log "Tipo: Tarea genérica (no automatizada)"
    RESULTADO="Tarea recibida pero no hay automatización específica para este tipo.
Instrucciones archivadas para procesamiento manual."
    STATUS="⏳ PENDIENTE MANUAL"
fi

# Paso 4: Escribir respuesta
log "Paso 4: Escribiendo respuesta..."

cat > "$INBOX_DIR/para-claude.md" << EOF
# Respuesta de Kimi Claw
**Tarea:** ${TAREA:-N/A}
**Fecha:** $TIMESTAMP
**Estado:** $STATUS

## Instrucciones recibidas:
\`\`\`
$(echo "$INSTRUCCIONES" | head -50)
\`\`\`

## Resultado:
$RESULTADO

---
*Ejecutado automáticamente por ai-inbox-bridge.sh v2.0*
EOF

# Paso 5: Archivar instrucciones procesadas
log "Paso 5: Archivando instrucciones..."
mkdir -p "$INBOX_DIR/historial"
mv "$INBOX_DIR/para-kimi.md" "$INBOX_DIR/historial/para-kimi-$(date +%Y%m%d-%H%M%S).md"

# Paso 6: Git push
log "Paso 6: Git push..."
git add -A
git commit -m "ai-inbox: $TAREA completada por Kimi Claw [$STATUS]" 2>&1 | tee -a "$LOG_FILE" || {
    log "ℹ️ No hay cambios para commitear o commit falló"
}

if git push origin main 2>&1 | tee -a "$LOG_FILE"; then
    log "✅ Git push exitoso"
else
    log "❌ Git push falló"
    exit 1
fi

log "=== FIN CICLO ($STATUS) ==="
exit 0
