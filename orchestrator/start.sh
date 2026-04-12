#!/usr/bin/env bash
# ─── ConflictZero Orchestrator — start.sh ─────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PID_FILE="$SCRIPT_DIR/orchestrator.pid"
LOG_FILE="$HOME/ConflictZero/reportes/orchestrator.log"

# Crea reportes dir si no existe
mkdir -p "$HOME/ConflictZero/reportes"

# Verifica que no esté ya corriendo
if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "El orquestador ya está corriendo (PID $PID)"
        exit 0
    else
        echo "PID file obsoleto, limpiando..."
        rm -f "$PID_FILE"
    fi
fi

# Crea virtualenv si no existe
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creando virtualenv..."
    python3 -m venv "$VENV_DIR"
fi

# Instala dependencias
echo "Instalando dependencias..."
"$VENV_DIR/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

# Carga .env si existe
ENV_FILE="$HOME/ConflictZero/.env"
if [[ -f "$ENV_FILE" ]]; then
    echo "Cargando variables de $ENV_FILE"
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
fi

# Lanza en background
echo "Iniciando orquestador..."
nohup "$VENV_DIR/bin/python" "$SCRIPT_DIR/main.py" >> "$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "Orquestador iniciado (PID $(cat "$PID_FILE"))"
echo "Log: $LOG_FILE"
