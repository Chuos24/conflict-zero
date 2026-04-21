#!/usr/bin/env python3
"""
Script de re-verificación diaria para "Mi Red" (Supplier Watchlist).
Se ejecuta vía cron cada día para detectar cambios en proveedores monitoreados.

Uso:
    python cron_daily_network_check.py [--dry-run]

Deploy:
    Render.com: Agregar como Cron Job en render.yaml
    Local: crontab -e -> 0 6 * * * cd /app && python scripts/cron_daily_network_check.py
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

# Añadir backend al path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, and_, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from app.models import (
    SupplierWatchlist, CompanySnapshot, SupplierAlert, 
    User, VerificationRequest
)
from app.core.config import settings
from app.services.data_collection import collect_all_data


@dataclass
class ChangeDetection:
    """Resultado de detección de cambio"""
    watchlist_id: str
    user_id: str
    supplier_ruc: str
    supplier_name: str
    change_type: str
    severity: str
    previous_status: str
    new_status: str
    details: Dict[str, Any]


class NetworkMonitor:
    """Monitor de red de proveedores"""
    
    def __init__(self, db: Session, dry_run: bool = False):
        self.db = db
        self.dry_run = dry_run
        self.changes_detected: List[ChangeDetection] = []
        self.stats = {
            "total_checked": 0,
            "changes_found": 0,
            "alerts_created": 0,
            "errors": 0
        }
    
    async def check_all_suppliers(self) -> Dict[str, Any]:
        """
        Re-verificar todos los proveedores activos en watchlists.
        """
        print(f"[{datetime.now().isoformat()}] Iniciando re-verificación diaria...")
        
        # Obtener todas las entradas activas
        watchlist_entries = self.db.query(SupplierWatchlist).filter(
            SupplierWatchlist.is_active == True
        ).all()
        
        print(f"  → {len(watchlist_entries)} proveedores en watchlists")
        
        for entry in watchlist_entries:
            try:
                await self._check_single_supplier(entry)
                self.stats["total_checked"] += 1
            except Exception as e:
                print(f"  ✗ Error verificando {entry.supplier_ruc}: {e}")
                self.stats["errors"] += 1
        
        # Crear alertas si no es dry-run
        if not self.dry_run and self.changes_detected:
            self._create_alerts()
        
        return self.stats
    
    async def _check_single_supplier(self, entry: SupplierWatchlist):
        """Verificar un proveedor individual"""
        ruc = entry.supplier_ruc
        
        # Obtener último snapshot conocido
        last_snapshot = None
        if entry.last_snapshot_id:
            last_snapshot = self.db.query(CompanySnapshot).filter(
                CompanySnapshot.id == entry.last_snapshot_id
            ).first()
        
        # Si no hay snapshot previo, buscar el más reciente por RUC
        if not last_snapshot:
            last_snapshot = self.db.query(CompanySnapshot).filter(
                CompanySnapshot.ruc == ruc
            ).order_by(desc(CompanySnapshot.snapshot_date)).first()
        
        # Obtener datos actuales de APIs
        try:
            current_data = await collect_all_data(ruc)
        except Exception as e:
            print(f"  ⚠ No se pudo obtener datos actuales para {ruc}: {e}")
            return
        
        # Crear nuevo snapshot
        new_snapshot = CompanySnapshot(
            ruc=ruc,
            sunat_status=current_data.get("sunat", {}).get("estado"),
            sunat_debt=current_data.get("sunat", {}).get("deuda", 0),
            sunat_num_trabajadores=current_data.get("sunat", {}).get("num_trabajadores"),
            osce_inhabilitado=current_data.get("osce", {}).get("inhabilitado", False),
            osce_sanciones_count=len(current_data.get("osce", {}).get("sanciones", [])),
            osce_sanciones_vigentes=current_data.get("osce", {}).get("sanciones_vigentes", 0),
            tce_sanciones_count=len(current_data.get("tce", {}).get("sanciones", [])),
            score_calculado=current_data.get("score"),
            source_api="cron_daily"
        )
        
        self.db.add(new_snapshot)
        self.db.flush()  # Para obtener el ID
        
        # Actualizar referencia en watchlist
        old_snapshot_id = entry.last_snapshot_id
        entry.last_snapshot_id = new_snapshot.id
        entry.last_checked_at = datetime.utcnow()
        
        # Detectar cambios si hay snapshot previo
        if last_snapshot:
            changes = self._detect_changes(entry, last_snapshot, new_snapshot, current_data)
            for change in changes:
                self.changes_detected.append(change)
                self.stats["changes_found"] += 1
                print(f"  ⚠ Cambio detectado: {ruc} - {change.change_type}")
        
        if not self.dry_run:
            self.db.commit()
    
    def _detect_changes(
        self, 
        entry: SupplierWatchlist,
        old: CompanySnapshot, 
        new: CompanySnapshot,
        current_data: Dict
    ) -> List[ChangeDetection]:
        """Detectar cambios significativos entre snapshots"""
        changes = []
        
        # 1. OSCE - Inhabilitación
        if entry.alert_on_osce and (not old.osce_inhabilitado and new.osce_inhabilitado):
            changes.append(ChangeDetection(
                watchlist_id=entry.id,
                user_id=entry.user_id,
                supplier_ruc=entry.supplier_ruc,
                supplier_name=entry.supplier_name or entry.supplier_ruc,
                change_type="osce_inhabilitado",
                severity="critical",
                previous_status="Habilitado",
                new_status="Inhabilitado OSCE",
                details={"sanciones": current_data.get("osce", {}).get("sanciones", [])}
            ))
        
        # 2. TCE - Nueva sanción
        if entry.alert_on_tce and new.tce_sanciones_count > old.tce_sanciones_count:
            new_sanctions = new.tce_sanciones_count - old.tce_sanciones_count
            changes.append(ChangeDetection(
                watchlist_id=entry.id,
                user_id=entry.user_id,
                supplier_ruc=entry.supplier_ruc,
                supplier_name=entry.supplier_name or entry.supplier_ruc,
                change_type="tce_nueva_sancion",
                severity="high",
                previous_status=f"{old.tce_sanciones_count} sanciones",
                new_status=f"{new.tce_sanciones_count} sanciones",
                details={"new_count": new_sanctions}
            ))
        
        # 3. OSCE - Nueva sanción
        if entry.alert_on_osce and new.osce_sanciones_vigentes > old.osce_sanciones_vigentes:
            changes.append(ChangeDetection(
                watchlist_id=entry.id,
                user_id=entry.user_id,
                supplier_ruc=entry.supplier_ruc,
                supplier_name=entry.supplier_name or entry.supplier_ruc,
                change_type="osce_nueva_sancion",
                severity="high",
                previous_status=f"{old.osce_sanciones_vigentes} sanciones vigentes",
                new_status=f"{new.osce_sanciones_vigentes} sanciones vigentes",
                details={}
            ))
        
        # 4. SUNAT - Deuda significativa
        if entry.alert_on_sunat_debt:
            debt_increase = new.sunat_debt - old.sunat_debt
            if debt_increase >= entry.alert_min_debt_amount:
                changes.append(ChangeDetection(
                    watchlist_id=entry.id,
                    user_id=entry.user_id,
                    supplier_ruc=entry.supplier_ruc,
                    supplier_name=entry.supplier_name or entry.supplier_ruc,
                    change_type="sunat_deuda_aumento",
                    severity="medium" if debt_increase < 10000 else "high",
                    previous_status=f"S/ {old.sunat_debt:,.2f}",
                    new_status=f"S/ {new.sunat_debt:,.2f}",
                    details={"increase": debt_increase}
                ))
        
        # 5. SUNAT - Cambio de estado (ACTIVO <-> SUSPENDIDO)
        if old.sunat_status != new.sunat_status and new.sunat_status:
            severity = "high" if "SUSPENDIDO" in (new.sunat_status or "") else "medium"
            changes.append(ChangeDetection(
                watchlist_id=entry.id,
                user_id=entry.user_id,
                supplier_ruc=entry.supplier_ruc,
                supplier_name=entry.supplier_name or entry.supplier_ruc,
                change_type="sunat_cambio_estado",
                severity=severity,
                previous_status=old.sunat_status or "Desconocido",
                new_status=new.sunat_status,
                details={}
            ))
        
        return changes
    
    def _create_alerts(self):
        """Crear registros de alertas en la base de datos"""
        for change in self.changes_detected:
            alert = SupplierAlert(
                user_id=change.user_id,
                supplier_ruc=change.supplier_ruc,
                supplier_name=change.supplier_name,
                change_type=change.change_type,
                previous_status=change.previous_status,
                new_status=change.new_status,
                severity=change.severity,
                is_read=False,
                email_sent=False
            )
            self.db.add(alert)
            self.stats["alerts_created"] += 1
        
        self.db.commit()
        print(f"  → {self.stats['alerts_created']} alertas creadas")


async def main():
    parser = argparse.ArgumentParser(
        description="Re-verificación diaria de proveedores en watchlists"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Simular sin crear alertas ni guardar cambios"
    )
    args = parser.parse_args()
    
    # Crear sesión de DB
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        monitor = NetworkMonitor(db, dry_run=args.dry_run)
        stats = await monitor.check_all_suppliers()
        
        print(f"\n[{datetime.now().isoformat()}] Resumen:")
        print(f"  • Proveedores verificados: {stats['total_checked']}")
        print(f"  • Cambios detectados: {stats['changes_found']}")
        print(f"  • Alertas creadas: {stats['alerts_created']}")
        print(f"  • Errores: {stats['errors']}")
        
        # Exit code para monitoreo
        sys.exit(0 if stats['errors'] == 0 else 1)
        
    except Exception as e:
        print(f"\n✗ Error fatal: {e}")
        sys.exit(2)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
