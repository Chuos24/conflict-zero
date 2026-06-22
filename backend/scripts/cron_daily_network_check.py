#!/usr/bin/env python3
"""
Cron Job: Re-verificación diaria de proveedores en "Mi Red"
Ejecutar diariamente a las 6:00 AM para detectar cambios en proveedores monitoreados.

Uso:
    python scripts/cron_daily_network_check.py
    
Configuración en Render (render.yaml):
    - schedule: "0 6 * * *"  # 6:00 AM diario
"""
import os
import sys
import logging
from datetime import datetime, timezone
from pathlib import Path

# Agregar el directorio padre al path para importar app
script_dir = Path(__file__).parent
backend_dir = script_dir.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar después de configurar el path
from app.core.config import get_settings
from app.models import CompanySnapshot, SupplierAlert, User
from app.routers.network import check_supplier_changes, send_alert_email

settings = get_settings()


def get_db_session():
    """Crea una sesión de base de datos."""
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def run_daily_network_check():
    """
    Ejecuta la re-verificación diaria de todos los proveedores monitoreados.
    """
    logger.info("=" * 60)
    logger.info(f"Iniciando re-verificación diaria de Mi Red - {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)
    
    db = get_db_session()
    
    try:
        # Obtener todos los RUCs únicos en watchlist
        from sqlalchemy import func
        
        watchlist_rucs = db.query(
            CompanySnapshot.ruc
        ).filter(
            CompanySnapshot.source_api == "watchlist"
        ).distinct().all()
        
        watchlist_rucs = [ruc[0] for ruc in watchlist_rucs]
        
        logger.info(f"Total proveedores en watchlist: {len(watchlist_rucs)}")
        
        if not watchlist_rucs:
            logger.info("No hay proveedores en watchlist. Nada que verificar.")
            return
        
        # Estadísticas
        total_checked = 0
        total_changes = 0
        total_alerts_created = 0
        total_emails_sent = 0
        
        for ruc in watchlist_rucs:
            logger.info(f"Verificando RUC: {ruc}")
            
            try:
                # Verificar cambios
                alerts = check_supplier_changes(db, ruc)
                total_checked += 1
                
                if alerts:
                    total_changes += 1
                    logger.info(f"  ⚠️  Cambios detectados: {len(alerts)}")
                    
                    # Obtener nombre del proveedor
                    latest_snapshot = db.query(CompanySnapshot).filter(
                        CompanySnapshot.ruc == ruc,
                        CompanySnapshot.source_api == "watchlist"
                    ).order_by(desc(CompanySnapshot.created_at)).first()
                    
                    supplier_name = latest_snapshot.supplier_name if latest_snapshot else None
                    
                    # Crear alertas en la base de datos
                    # Encontrar usuarios que tienen este proveedor en su red
                    # (Para simplificar, asumimos que todas las alertas van a todos los usuarios admin por ahora)
                    # En una implementación real, necesitaríamos una tabla de relación user-supplier
                    
                    for alert_data in alerts:
                        # Crear alerta (sin user_id específico por ahora - se asigna al primer admin)
                        admin_users = db.query(User).filter(User.is_admin == True).all()
                        
                        for admin in admin_users:
                            alert = SupplierAlert(
                                user_id=admin.id,
                                supplier_ruc=ruc,
                                supplier_name=supplier_name,
                                change_type=alert_data["change_type"],
                                previous_status=alert_data["previous_status"],
                                new_status=alert_data["new_status"],
                                severity=alert_data["severity"],
                                is_read=False,
                                email_sent=False
                            )
                            db.add(alert)
                            total_alerts_created += 1
                        
                        db.commit()
                    
                    # Enviar emails a admins
                    for admin in admin_users:
                        try:
                            email_sent = send_alert_email(admin.email, ruc, alerts, db)
                            if email_sent:
                                total_emails_sent += 1
                                # Marcar alertas como email enviado
                                db.query(SupplierAlert).filter(
                                    SupplierAlert.supplier_ruc == ruc,
                                    SupplierAlert.user_id == admin.id,
                                    SupplierAlert.email_sent == False
                                ).update({
                                    "email_sent": True,
                                    "email_sent_at": datetime.now(timezone.utc)
                                })
                                db.commit()
                        except Exception as e:
                            logger.error(f"Error enviando email a {admin.email}: {e}")
                else:
                    logger.info(f"  ✅ Sin cambios")
                    
            except Exception as e:
                logger.error(f"Error verificando RUC {ruc}: {e}")
                continue
        
        # Resumen
        logger.info("=" * 60)
        logger.info("RESUMEN DE RE-VERIFICACIÓN")
        logger.info("=" * 60)
        logger.info(f"Total verificados: {total_checked}")
        logger.info(f"Proveedores con cambios: {total_changes}")
        logger.info(f"Alertas creadas: {total_alerts_created}")
        logger.info(f"Emails enviados: {total_emails_sent}")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"Error en re-verificación diaria: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_daily_network_check()
