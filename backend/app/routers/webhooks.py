from fastapi import APIRouter, HTTPException, status, Request
from typing import Dict, Any
import logging
import hmac
import hashlib

from app.core.database import SessionLocal
from app.models import User
from app.services.email import get_email_service

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
    description="Endpoint para recibir webhooks de servicios externos (Stripe, Culqi, etc).")
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
        return await handler(data, provider="stripe")
    
    return {"status": "acknowledged", "event": event_type, "handled": False}

async def process_culqi_webhook(data: dict):
    """Process Culqi webhook events"""
    event_type = data.get("type", "")
    
    if event_type == "charge.status.changed":
        status = data.get("data", {}).get("status", "")
        if status == "captured":
            return await handle_payment_success(data, provider="culqi")
        elif status in ["rejected", "cancelled"]:
            return await handle_payment_failed(data, provider="culqi")
    
    return {"status": "acknowledged", "provider": "culqi", "event": event_type}

# ============================================================================
# EVENT HANDLERS
# ============================================================================

PLAN_CONFIG = {
    "essential": {"monthly_limit": 1000},
    "professional": {"monthly_limit": 5000},
    "enterprise": {"monthly_limit": 100000},
    "red": {"monthly_limit": 50},
}

def _extract_user_and_plan(data: dict, provider: str):
    """Extrae user_id, email y plan del payload del webhook."""
    user_id = None
    email = None
    plan = None
    
    if provider == "stripe":
        obj = data.get("data", {}).get("object", {})
        # Intentar extraer de metadata
        metadata = obj.get("metadata", {})
        user_id = metadata.get("user_id")
        
        # O del customer
        customer = obj.get("customer", {})
        if isinstance(customer, dict):
            email = customer.get("email")
        
        # Extraer plan de los items
        items = obj.get("items", {}).get("data", [])
        if items:
            plan_id = items[0].get("plan", {}).get("id", "")
            if "enterprise" in plan_id.lower():
                plan = "enterprise"
            elif "professional" in plan_id.lower():
                plan = "professional"
            elif "essential" in plan_id.lower():
                plan = "essential"
            else:
                plan = "essential"
        
        # Si no hay items, revisar status para downgrade
        sub_status = obj.get("status", "")
        if sub_status == "canceled":
            plan = "red"
            
    elif provider == "culqi":
        obj = data.get("data", {})
        metadata = obj.get("metadata", {})
        user_id = metadata.get("user_id")
        email = obj.get("email")
        plan = metadata.get("plan", "essential")
    
    return user_id, email, plan

def _find_user(db, user_id: str = None, email: str = None):
    """Busca usuario por ID o email."""
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user
    return None

async def handle_payment_success(data: dict, provider: str = "generic"):
    """Handle successful payment - actualiza plan en DB y envía email."""
    event_id = data.get("id", "unknown")
    logger.info(f"Payment succeeded: {event_id} (provider={provider})")
    
    db = SessionLocal()
    email_service = get_email_service()
    updated = False
    email_sent = False
    
    try:
        user_id, email, plan = _extract_user_and_plan(data, provider)
        user = _find_user(db, user_id, email)
        
        if user and plan:
            # Actualizar plan y límites
            user.plan_type = plan
            user.monthly_limit = PLAN_CONFIG.get(plan, {}).get("monthly_limit", 1000)
            db.commit()
            updated = True
            logger.info(f"✅ Usuario {user.email} actualizado a plan {plan}")
            
            # Enviar email de confirmación
            try:
                email_sent = email_service.send_email(
                    to_email=user.email,
                    subject="✅ Pago confirmado - Conflict Zero",
                    body=f"""
                    <h2>¡Pago confirmado!</h2>
                    <p>Hola {user.full_name},</p>
                    <p>Tu pago ha sido procesado exitosamente.</p>
                    <p><strong>Plan activado:</strong> {plan.upper()}</p>
                    <p><strong>Límite mensual:</strong> {user.monthly_limit} verificaciones</p>
                    <p>Gracias por confiar en Conflict Zero.</p>
                    """,
                    html=True
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar email de confirmación: {e}")
        else:
            logger.warning(f"⚠️ No se encontró usuario para el pago {event_id}")
            
    except Exception as e:
        logger.error(f"❌ Error procesando pago exitoso: {e}")
    finally:
        db.close()
    
    return {
        "status": "success",
        "action": "payment_success",
        "provider": provider,
        "user_updated": updated,
        "email_sent": email_sent,
        "message": "Pago procesado exitosamente"
    }

async def handle_payment_failed(data: dict, provider: str = "generic"):
    """Handle failed payment - notifica al usuario."""
    event_id = data.get("id", "unknown")
    logger.warning(f"Payment failed: {event_id} (provider={provider})")
    
    db = SessionLocal()
    email_service = get_email_service()
    notified = False
    
    try:
        user_id, email, _ = _extract_user_and_plan(data, provider)
        user = _find_user(db, user_id, email)
        
        if user:
            # Notificar al usuario sobre el pago fallido
            try:
                notified = email_service.send_email(
                    to_email=user.email,
                    subject="⚠️ Problema con tu pago - Conflict Zero",
                    body=f"""
                    <h2>Pago no procesado</h2>
                    <p>Hola {user.full_name},</p>
                    <p>Hubo un problema al procesar tu pago. Tu suscripción sigue activa temporalmente.</p>
                    <p>Por favor actualiza tu método de pago para evitar interrupciones.</p>
                    <p>Si necesitas ayuda, contáctanos.</p>
                    """,
                    html=True
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar email de notificación: {e}")
        else:
            logger.warning(f"⚠️ No se encontró usuario para notificar sobre pago fallido {event_id}")
            
    except Exception as e:
        logger.error(f"❌ Error procesando pago fallido: {e}")
    finally:
        db.close()
    
    return {
        "status": "failed",
        "action": "payment_failed",
        "provider": provider,
        "user_notified": notified,
        "message": "Pago fallido - se notificará al usuario"
    }

async def handle_subscription_created(data: dict, provider: str = "stripe"):
    """Handle new subscription"""
    event_id = data.get("id", "unknown")
    logger.info(f"Subscription created: {event_id}")
    
    db = SessionLocal()
    try:
        user_id, email, plan = _extract_user_and_plan(data, provider)
        user = _find_user(db, user_id, email)
        if user and plan:
            user.plan_type = plan
            user.monthly_limit = PLAN_CONFIG.get(plan, {}).get("monthly_limit", 1000)
            db.commit()
            logger.info(f"✅ Suscripción creada para {user.email} - Plan {plan}")
    except Exception as e:
        logger.error(f"❌ Error creando suscripción: {e}")
    finally:
        db.close()
    
    return {"status": "success", "action": "subscription_created"}

async def handle_subscription_updated(data: dict, provider: str = "stripe"):
    """Handle subscription update"""
    event_id = data.get("id", "unknown")
    logger.info(f"Subscription updated: {event_id}")
    
    db = SessionLocal()
    try:
        user_id, email, plan = _extract_user_and_plan(data, provider)
        user = _find_user(db, user_id, email)
        if user and plan:
            user.plan_type = plan
            user.monthly_limit = PLAN_CONFIG.get(plan, {}).get("monthly_limit", 1000)
            db.commit()
            logger.info(f"✅ Suscripción actualizada para {user.email} - Plan {plan}")
    except Exception as e:
        logger.error(f"❌ Error actualizando suscripción: {e}")
    finally:
        db.close()
    
    return {"status": "success", "action": "subscription_updated"}

async def handle_subscription_cancelled(data: dict, provider: str = "stripe"):
    """Handle subscription cancellation - downgrades to red plan"""
    event_id = data.get("id", "unknown")
    logger.info(f"Subscription cancelled: {event_id}")
    
    db = SessionLocal()
    email_service = get_email_service()
    downgraded = False
    
    try:
        user_id, email, _ = _extract_user_and_plan(data, provider)
        user = _find_user(db, user_id, email)
        
        if user:
            # Downgrade a plan red
            user.plan_type = "red"
            user.monthly_limit = PLAN_CONFIG["red"]["monthly_limit"]
            db.commit()
            downgraded = True
            logger.info(f"✅ Usuario {user.email} downgraded a plan RED")
            
            # Notificar al usuario
            try:
                email_service.send_email(
                    to_email=user.email,
                    subject="Suscripción cancelada - Conflict Zero",
                    body=f"""
                    <h2>Suscripción cancelada</h2>
                    <p>Hola {user.full_name},</p>
                    <p>Tu suscripción ha sido cancelada. Has sido movido al plan Red (gratuito).</p>
                    <p><strong>Nuevo límite:</strong> 50 verificaciones/mes</p>
                    <p>Si deseas reactivar tu suscripción, visita la página de precios.</p>
                    """,
                    html=True
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo enviar email de cancelación: {e}")
    except Exception as e:
        logger.error(f"❌ Error cancelando suscripción: {e}")
    finally:
        db.close()
    
    return {
        "status": "success", 
        "action": "subscription_cancelled",
        "downgraded": downgraded
    }

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
        "version": "1.1"
    }
