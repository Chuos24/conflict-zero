#!/usr/bin/env python3
"""
Script de monitoreo de SLA para Conflict Zero
Ejecutado cada 30 minutos vía cron
"""
import requests
import json
import os
from datetime import datetime

# Configuración
API_BASE = "https://conflict-zero-api.onrender.com/api/v1"
SLA_THRESHOLD = 99.9  # Porcentaje mínimo de uptime
ALERT_WEBHOOK = os.getenv("ALERT_WEBHOOK_URL")  # Opcional: URL para alertas

def check_health():
    """Verifica el health endpoint."""
    try:
        response = requests.get(f"{API_BASE}/health", timeout=30)
        data = response.json()
        
        is_healthy = data.get("status") == "healthy"
        sla_metrics = data.get("sla", {})
        uptime_pct = sla_metrics.get("uptime_percentage", 0)
        
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy" if is_healthy else "degraded",
            "uptime_percentage": uptime_pct,
            "sla_breach": uptime_pct < SLA_THRESHOLD,
            "services": data.get("services", {})
        }
        
        # Guardar resultado
        with open("/tmp/health_check_latest.json", "w") as f:
            json.dump(result, f, indent=2)
        
        # Alertar si hay breach de SLA
        if result["sla_breach"]:
            print(f"⚠️ ALERTA: SLA breach detectado - {uptime_pct}% uptime")
            # Aquí se puede enviar alerta a webhook/email
        
        return result
        
    except Exception as e:
        error_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "error",
            "error": str(e),
            "sla_breach": True
        }
        print(f"❌ ERROR: {e}")
        return error_result

if __name__ == "__main__":
    print(f"[{datetime.utcnow().isoformat()}] Iniciando health check...")
    result = check_health()
    print(f"Status: {result['status']}")
    print(f"Uptime: {result.get('uptime_percentage', 'N/A')}%")
    
    if result.get('sla_breach'):
        print("⚠️ SLA BREACH DETECTADO")
        exit(1)
    else:
        print("✅ SLA OK")
        exit(0)
