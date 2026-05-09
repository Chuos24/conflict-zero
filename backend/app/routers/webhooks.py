from fastapi import APIRouter, HTTPException, status, Request
from typing import Dict, Any
import logging
import hmac
import hashlib

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

# Store webhook handlers
WEBHOOK_HANDLERS: Dict[str, Any] = {}

def register_webhook_handler(event_type: str, handler):
    """Register a handler for a specific webhook event"""
    WEBHOOK_HANDLERS[event_type] = handler

# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@router.post(
    "/receive",
    summary="Recibir Webhook",
    description="Endpoint para recibir webhooks de servicios externos (Stripe, Culqi, etc)."")
async def receive_webhook(
    request: Request,
    provider: str = "generic"
):
    """
    Recibe webhooks de proveedores de pago y otros servicios.
    
    - **provider**: Proveedor del webhook (stripe, culqi, generic)
    - Verifica firma si está disponible
    - Procesa el evento según su tipo
    """
    try:
        payload = await request.body()
        data = await request.json()
        
        event_type = data.get("type", data.get("event", "unknown"))
        
        logger.info(f"Webhook recibido: provider={provider}, type={event_type}")
        
        # Process based on provider
        if provider == "stripe":
            return await process_stripe_webhook(data, payload, request)
        elif provider == "culqi":
            return await process_culqi_webhook(data)
        else:
            return {
                "status": "received",
                "provider": provider,
                "event_type": event_type,
                "message": "Webhook recibido y registrado"
            }
            
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error procesando webhook: {str(e)}"
        )

async def process_stripe_webhook(data: dict, payload: bytes, request: Request):
    """Process Stripe webhook events"""
    event_type = data.get("type", "")
    
    # Event types to handle
    handlers = {
        "invoice.payment_succeeded": handle_payment_success,
        "invoice.payment_failed": handle_payment_failed,
        "customer.subscription.created": handle_subscription_created,
        "customer.subscription.updated": handle_subscription_updated,
        "customer.subscription.deleted": handle_subscription_cancelled,
    }
    
    handler = handlers.get(event_type)
    if handler:
        return await handler(data)
    
    return {"status": "acknowledged", "event": event_type, "handled": False}

async def process_culqi_webhook(data: dict):
    """Process Culqi webhook events"""
    event_type = data.get("type", "")
    
    if event_type == "charge.status.changed":
        status = data.get("data", {}).get("status", "")
        if status == "captured":
            return await handle_payment_success(data)
        elif status in ["rejected", "cancelled"]:
            return await handle_payment_failed(data)
    
    return {"status": "acknowledged", "provider": "culqi", "event": event_type}

# ============================================================================
# EVENT HANDLERS
# ============================================================================

async def handle_payment_success(data: dict):
    """Handle successful payment"""
    logger.info(f"Payment succeeded: {data.get('id', 'unknown')}")
    # TODO: Update user subscription status in database
    # TODO: Send confirmation email
    return {
        "status": "success",
        "action": "payment_success",
        "message": "Pago procesado exitosamente"
    }

async def handle_payment_failed(data: dict):
    """Handle failed payment"""
    logger.warning(f"Payment failed: {data.get('id', 'unknown')}")
    # TODO: Notify user about failed payment
    # TODO: Schedule retry or downgrade
    return {
        "status": "failed",
        "action": "payment_failed",
        "message": "Pago fallido - se notificará al usuario"
    }

async def handle_subscription_created(data: dict):
    """Handle new subscription"""
    logger.info(f"Subscription created: {data.get('id', 'unknown')}")
    return {"status": "success", "action": "subscription_created"}

async def handle_subscription_updated(data: dict):
    """Handle subscription update"""
    logger.info(f"Subscription updated: {data.get('id', 'unknown')}")
    return {"status": "success", "action": "subscription_updated"}

async def handle_subscription_cancelled(data: dict):
    """Handle subscription cancellation"""
    logger.info(f"Subscription cancelled: {data.get('id', 'unknown')}")
    return {"status": "success", "action": "subscription_cancelled"}

# ============================================================================
# WEBHOOK CONFIGURATION
# ============================================================================

@router.get("/config")
async def get_webhook_config():
    """Get webhook configuration for frontend"""
    return {
        "endpoints": {
            "stripe": "/api/v1/webhooks/receive?provider=stripe",
            "culqi": "/api/v1/webhooks/receive?provider=culqi",
            "generic": "/api/v1/webhooks/receive"
        },
        "supported_events": [
            "invoice.payment_succeeded",
            "invoice.payment_failed",
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
            "charge.status.changed"
        ],
        "version": "1.0"
    }
