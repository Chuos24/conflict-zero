#!/bin/bash
# daily-standup-agent.sh
# Cada día analiza ConflictZero, identifica las 3 prioridades más importantes,
# y escribe instrucciones detalladas en ai-inbox/para-claude.md

set -e

REPO_DIR="/root/.openclaw/workspace/conflict-zero"
INBOX_DIR="$REPO_DIR/ai-inbox"
LOG_FILE="/var/log/daily-standup-agent.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE=$(date '+%Y-%m-%d')

log() {
    echo "[$TIMESTAMP] $1" | tee -a "$LOG_FILE"
}

log "=== DAILY STANDUP AGENT INICIADO ==="

cd "$REPO_DIR" || {
    log "ERROR: No se puede acceder a $REPO_DIR"
    exit 1
}

# ============================================
# FASE 1: RECOPILACIÓN DE DATOS
# ============================================

log "Fase 1: Recopilando datos..."

# Health checks
HEALTH_API=$(curl -s -o /dev/null -w "%{http_code}" "https://conflict-zero-api.onrender.com/api/v1/health" || echo "000")
HEALTH_LANDING=$(curl -s -o /dev/null -w "%{http_code}" "https://czperu.com" || echo "000")

# Últimos commits
LAST_COMMITS=$(git log --oneline -5 || echo "N/A")
COMMITS_LAST_24H=$(git log --since="24 hours ago" --oneline | wc -l)

# Buscar TODOs críticos
TODOS_BACKEND=$(grep -rn "TODO\|FIXME\|HACK\|XXX" app/ --include="*.py" 2>/dev/null | head -15 || echo "Ninguno")

# Verificar endpoints críticos
NETWORK_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://conflict-zero-api.onrender.com/api/v3/network/" -H "Authorization: Bearer CZ2026ADM" || echo "000")
PENDING_PAYMENTS=$(curl -s "https://conflict-zero-api.onrender.com/api/v3/admin/pending-activations" -H "Authorization: Bearer CZ2026ADM" 2>/dev/null | grep -o '"unactivated_count":[0-9]*' | cut -d: -f2 || echo "0")

# Verificar tareas previas pendientes
PREV_UNRESOLVED=0
if [ -f "$INBOX_DIR/para-claude.md" ]; then
    LAST_TASK_DATE=$(stat -c %Y "$INBOX_DIR/para-claude.md")
    NOW=$(date +%s)
    AGE_HOURS=$(( (NOW - LAST_TASK_DATE) / 3600 ))
    if [ "$AGE_HOURS" -lt 48 ]; then
        PREV_UNRESOLVED=$(grep -c "⏳ PENDIENTE\|❌ BLOQUEADO" "$INBOX_DIR/para-claude.md" 2>/dev/null || echo 0)
    fi
fi

log "Health API=$HEALTH_API Landing=$HEALTH_LANDING Network=$NETWORK_STATUS"
log "Commits 24h=$COMMITS_LAST_24H Pagos pendientes=$PENDING_PAYMENTS"

# ============================================
# FASE 2: IDENTIFICAR 3 PRIORIDADES
# ============================================

log "Fase 2: Identificando prioridades..."

P1=""
P2=""
P3=""

# P0: Algo caído
if [ "$HEALTH_API" != "200" ]; then
    P1="P0-API: El health endpoint devuelve $HEALTH_API. Investigar logs de Render y fix urgente."
fi

if [ -z "$P1" ]; then
    P1="P1-MI-RED-EMAILS: Mi Red ya tiene endpoints y grafo D3.js, pero falta el envío automático de emails cuando el cron job network-monitor-daily detecte cambios. Implementar el hook de email en app/jobs/network_monitor.py usando el router de notificaciones existente."
fi

if [ -z "$P2" ]; then
    if [ "$PENDING_PAYMENTS" != "0" ] && [ -n "$PENDING_PAYMENTS" ]; then
        P2="P1-PAGOS: Hay $PENDING_PAYMENTS usuario(s) con pago registrado pero plan sin activar. Revisar /api/v3/admin/pending-activations y activar manualmente los planes correspondientes."
    else
        P2="P2-CACHE-ZAMORA: El RUC 20529400790 muestra score incorrecto por problema de cache en Render. Forzar redeploy manual desde Render Dashboard o limpiar caché de la instancia."
    fi
fi

if [ -z "$P3" ]; then
    if echo "$TODOS_BACKEND" | grep -q "TODO"; then
        CRITICAL_TODO=$(echo "$TODOS_BACKEND" | grep "TODO" | head -1 | sed 's/^[[:space:]]*//')
        P3="P2-CODIGO: Hay TODOs pendientes en backend que requieren atención. El más urgente: $CRITICAL_TODO"
    else
        P3="P2-CONSOLIDAR-MODELADO: Actualizar MEMORY.md y CONFLICT_ZERO_PLAN.md para reflejar que Mi Red ya está parcialmente en producción (endpoints listos, falta email hook y cron job de verificación)."
    fi
fi

# ============================================
# FASE 3: ESCRIBIR PARA-CLAUDE.MD
# ============================================

log "Fase 3: Escribiendo para-claude.md..."

mkdir -p "$INBOX_DIR"

cat > "$INBOX_DIR/para-claude.md" << EOF
# Daily Standup — Conflict Zero
**Fecha:** $DATE
**Agente:** Kimi Claw
**Estado:** Generado automáticamente

---

## Resumen del Sistema (últimas 24h)

| Métrica | Valor |
|---------|-------|
| Health API | $HEALTH_API |
| Health Landing | $HEALTH_LANDING |
| Network Endpoint | $NETWORK_STATUS |
| Commits últimas 24h | $COMMITS_LAST_24H |
| Pagos sin activar | $PENDING_PAYMENTS |
| Tareas previas pendientes | $PREV_UNRESOLVED |

### Últimos commits:
\`\`\`
$LAST_COMMITS
\`\`\`

---

## 🎯 3 TAREAS PRIORITARIAS PARA HOY

### 1. $P1

**Instrucciones detalladas:**
- Investiga el problema o la oportunidad mencionada arriba
- Implementa la solución más simple y segura
- Si requiere decisión estratégica o gasto de dinero, escribe el bloqueo en ai-inbox/para-kimi.md
- Si puedes resolverlo solo, commitea con mensaje descriptivo y pushea

### 2. $P2

**Instrucciones detalladas:**
- Investiga el problema o la oportunidad mencionada arriba
- Implementa la solución más simple y segura
- Si requiere decisión estratégica o gasto de dinero, escribe el bloqueo en ai-inbox/para-kimi.md
- Si puedes resolverlo solo, commitea con mensaje descriptivo y pushea

### 3. $P3

**Instrucciones detalladas:**
- Investiga el problema o la oportunidad mencionada arriba
- Implementa la solución más simple y segura
- Si requiere decisión estratégica o gasto de dinero, escribe el bloqueo en ai-inbox/para-kimi.md
- Si puedes resolverlo solo, commitea con mensaje descriptivo y pushea

---

## 📋 PROTOCOLO PARA CLAUDE

**Instrucción única:**
> Procesa todas las tareas pendientes de Kimi en para-claude.md

**Flujo:**
1. Lee CONFLICT_ZERO_PLAN.md para contexto
2. Lee este archivo (para-claude.md)
3. Ordena las 3 tareas por esfuerzo/impacto
4. Toma la primera y resuélvela
5. Cuando termines, actualiza este archivo marcando la tarea como ✅ completada
6. Si te queda tiempo, continúa con la siguiente
7. Al final del día, escribe un breve resumen de lo logrado

**Regla Dark Factory:** Si algo te bloquea o no sabes cómo decidir, NO te quedes parado. Escribe el bloqueo en ai-inbox/para-kimi.md y continúa con otra tarea. Solo avisamos a Santiago si es rojo (gasto, seguridad, arquitectura, precios).

---

## 🔍 Datos adicionales

### TODOs en backend:
\`\`\`
$TODOS_BACKEND
\`\`\`

---
*Generado automáticamente por daily-standup-agent.sh*
EOF

log "Fase 4: Git push..."

git add ai-inbox/para-claude.md scripts/daily-standup-agent.sh 2>/dev/null || true
git commit -m "daily-standup: $DATE — 3 tareas prioritarias generadas" || log "Nada nuevo para commitear"
git push origin main || log "Push falló o no necesario"

log "=== DAILY STANDUP COMPLETADO ==="
