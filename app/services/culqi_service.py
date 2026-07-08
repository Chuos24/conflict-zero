"""
Culqi Payment Service — Conflict Zero

Integración con Culqi (pasarela de pagos peruana) para procesar pagos de planes.
Docs: https://docs.culqi.com/
"""
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime

log = logging.getLogger(__name__)

# ─── Configuración ──────────────────────────────────────────────────────────

CULQI_PUBLIC_KEY = os.environ.get("CULQI_PUBLIC_KEY", "")
CULQI_SECRET_KEY = os.environ.get("CULQI_SECRET_KEY", "")
CULQI_API_BASE = "https://api.culqi.com/v2"

# Precios en céntimos (soles * 100)
PLAN_PRICES_CENTS = {
    "essential": 400 * 100,      # S/ 400.00
    "professional": 800 * 100,   # S/ 800.00
    "enterprise": 2500 * 100,    # S/ 2,500.00
}

PLAN_NAMES = {
    "essential": "Plan Essential",
    "professional": "Plan Professional",
    "enterprise": "Plan Enterprise",
}


class CulqiService:
    """Servicio de integración con Culqi para cobros recurrentes."""

    def __init__(self):
        self.secret_key = CULQI_SECRET_KEY
        self.public_key = CULQI_PUBLIC_KEY
        self.enabled = bool(self.secret_key and self.public_key)

    def is_configured(self) -> bool:
        return self.enabled

    def get_plan_config(self) -> Dict[str, Any]:
        """Devuelve la configuración de precios para el frontend."""
        return {
            "public_key": self.public_key if self.enabled else None,
            "currency": "PEN",
            "plans": {
                plan: {
                    "amount": price,
                    "amount_display": f"S/ {price / 100:,.2f}",
                    "name": PLAN_NAMES[plan],
                }
                for plan, price in PLAN_PRICES_CENTS.items()
            },
        }

    def create_charge(self, token: str, amount: int, currency: str, email: str,
                     description: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Crea un cargo (charge) usando un token de tarjeta.
        
        Args:
            token: Token generado por Culqi.js en el frontend
            amount: Monto en céntimos
            currency: Código de moneda (PEN)
            email: Email del cliente
            description: Descripción del cargo
            metadata: Datos adicionales
        """
        if not self.enabled:
            return {"success": False, "error": "Culqi no está configurado"}

        import requests

        payload = {
            "amount": amount,
            "currency_code": currency,
            "email": email,
            "description": description,
            "source_id": token,
        }
        if metadata:
            payload["metadata"] = metadata

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{CULQI_API_BASE}/charges",
                json=payload,
                headers=headers,
                timeout=30,
            )
            data = response.json()

            if response.status_code == 201:
                return {
                    "success": True,
                    "charge_id": data.get("id"),
                    "amount": data.get("amount"),
                    "currency": data.get("currency_code"),
                    "status": data.get("status"),  # captured, pending, refunded
                    "created_at": data.get("creation_date"),
                    "receipt_url": data.get("receipt_url"),
                    "raw": data,
                }
            else:
                error_msg = data.get("message", "Error desconocido")
                error_type = data.get("type", "unknown")
                log.error(f"Culqi charge error: {error_type} — {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "error_type": error_type,
                    "raw": data,
                }

        except requests.RequestException as exc:
            log.error(f"Culqi request error: {exc}")
            return {"success": False, "error": f"Error de conexión: {str(exc)}"}
        except Exception as exc:
            log.error(f"Culqi unexpected error: {exc}")
            return {"success": False, "error": str(exc)}

    def create_subscription(self, card_token: str, plan_key: str, email: str,
                           metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Crea una suscripción recurrente (plan).
        Requiere plan configurado en dashboard de Culqi.
        """
        # Por ahora, delegamos a create_charge con metadata de suscripción
        # Culqi requiere configurar planes en su dashboard para suscripciones nativas
        amount = PLAN_PRICES_CENTS.get(plan_key)
        if not amount:
            return {"success": False, "error": f"Plan '{plan_key}' no encontrado"}

        description = f"Suscripción {PLAN_NAMES.get(plan_key, plan_key)} — Conflict Zero"
        return self.create_charge(
            token=card_token,
            amount=amount,
            currency="PEN",
            email=email,
            description=description,
            metadata=metadata or {},
        )

    def get_charge(self, charge_id: str) -> Dict[str, Any]:
        """Obtiene el estado de un cargo existente."""
        if not self.enabled:
            return {"success": False, "error": "Culqi no está configurado"}

        import requests

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(
                f"{CULQI_API_BASE}/charges/{charge_id}",
                headers=headers,
                timeout=30,
            )
            data = response.json()

            if response.status_code == 200:
                return {"success": True, "charge": data}
            else:
                return {
                    "success": False,
                    "error": data.get("message", "Cargo no encontrado"),
                    "raw": data,
                }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def refund_charge(self, charge_id: str, amount: Optional[int] = None) -> Dict[str, Any]:
        """Crea una devolución (refund) para un cargo."""
        if not self.enabled:
            return {"success": False, "error": "Culqi no está configurado"}

        import requests

        payload = {"charge_id": charge_id}
        if amount:
            payload["amount"] = amount

        headers = {
            "Authorization": f"Bearer {self.secret_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                f"{CULQI_API_BASE}/refunds",
                json=payload,
                headers=headers,
                timeout=30,
            )
            data = response.json()

            if response.status_code == 201:
                return {"success": True, "refund": data}
            else:
                return {
                    "success": False,
                    "error": data.get("message", "Error en devolución"),
                    "raw": data,
                }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def validate_webhook(self, headers: Dict[str, str], body: str, signature: str) -> bool:
        """
        Valida la firma de un webhook de Culqi.
        Culqi envía un header 'X-Culqi-Signature' con HMAC-SHA256.
        """
        if not self.secret_key:
            return False

        import hmac
        import hashlib

        expected = hmac.new(
            self.secret_key.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Timing-safe comparison
        return hmac.compare_digest(expected, signature)


# Singleton
culqi_service = CulqiService()
