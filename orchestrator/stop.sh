#!/usr/bin/env bash
# ─── ConflictZero Orchestrator — stop.sh ──────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/orchestrator.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "No se encontró PID file. El orquestador no está corriendo."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill -0 "$PID" 2>/dev/null; then
    echo "Deteniendo orquestador (PID $PID)..."
    kill "$PID"
    sleep 1
    if kill -0 "$PID" 2>/dev/null; then
        echo "Forzando cierre..."
        kill -9 "$PID"
    fi
    rm -f "$PID_FILE"
    echo "Orquestador detenido."
else
    echo "El proceso $PID no existe. Limpiando PID file."
    rm -f "$PID_FILE"
fi
