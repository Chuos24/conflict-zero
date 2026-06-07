"""
Servicio de Snapshots para ML-Ready Architecture.

Guarda automáticamente el estado de cada empresa consultada
para construir dataset de time-series para ML futuro.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models import CompanySnapshot, SupplierAlert, User
from app.core.database import SessionLocal
from app.services.email_service import email_service


class SnapshotService:
    """
    Servicio para guardar y consultar snapshots de empresas.
    
    Uso:
        snapshot_service = SnapshotService(db)
        snapshot_service.save_snapshot(ruc="20100123091", data={...})
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def save_snapshot(
        self,
        ruc: str,
        sunat_data: Optional[Dict] = None,
        osce_data: Optional[Dict] = None,
        tce_data: Optional[Dict] = None,
        score_data: Optional[Dict] = None,
        source_api: str = "decolecta",
        query_id: Optional[str] = None
    ) -> CompanySnapshot:
        """
        Guarda un snapshot del estado actual de una empresa.
        
        Args:
            ruc: RUC de la empresa
            sunat_data: Datos de SUNAT
            osce_data: Datos de OSCE
            tce_data: Datos de TCE
            score_data: Score calculado y contribuciones
            source_api: Fuente de los datos
            query_id: ID de la verificación relacionada
        """
        # Calcular hash de los datos para detectar cambios
        raw_data = {
            "sunat": sunat_data or {},
            "osce": osce_data or {},
            "tce": tce_data or {}
        }
        raw_data_hash = hashlib.sha256(
            json.dumps(raw_data, sort_keys=True).encode()
        ).hexdigest()[:64]
        
        # Extraer datos SUNAT
        sunat_status = None
        sunat_debt = 0.0
        sunat_num_trabajadores = None
        sunat_ultimo_pago = None
        dias_ultimo_pago = None
        
        if sunat_data:
            sunat_status = sunat_data.get("estado_contribuyente", sunat_data.get("estado"))
            sunat_debt = float(sunat_data.get("deuda_coactiva", 0) or 0)
            sunat_num_trabajadores = sunat_data.get("num_trabajadores")
            
            # Calcular días desde último pago si hay fecha
            ultimo_pago_str = sunat_data.get("ultimo_pago")
            if ultimo_pago_str:
                try:
                    sunat_ultimo_pago = datetime.strptime(ultimo_pago_str, "%Y-%m-%d")
                    dias_ultimo_pago = (datetime.utcnow() - sunat_ultimo_pago).days
                except:
                    pass
        
        # Extraer datos OSCE
        osce_inhabilitado = False
        osce_sanciones_count = 0
        osce_sanciones_vigentes = 0
        osce_sanciones_historicas = 0
        osce_ultima_sancion_fecha = None
        dias_ultima_sancion_osce = None
        
        if osce_data:
            osce_inhabilitado = osce_data.get("inhabilitado", False)
            osce_sanciones_count = len(osce_data.get("sanciones", []))
            osce_sanciones_vigentes = osce_data.get("sanciones_vigentes", 0)
            osce_sanciones_historicas = osce_data.get("sanciones_historicas", 0)
            
            # Fecha de última sanción
            ultima_sancion = osce_data.get("ultima_sancion_fecha")
            if ultima_sancion:
                try:
                    osce_ultima_sancion_fecha = datetime.strptime(ultima_sancion, "%Y-%m-%d")
                    dias_ultima_sancion_osce = (datetime.utcnow() - osce_ultima_sancion_fecha).days
                except:
                    pass
        
        # Extraer datos TCE
        tce_sanciones_count = 0
        tce_ultima_sancion_fecha = None
        
        if tce_data:
            tce_sanciones_count = len(tce_data.get("sanciones", []))
            ultima_tce = tce_data.get("ultima_sancion_fecha")
            if ultima_tce:
                try:
                    tce_ultima_sancion_fecha = datetime.strptime(ultima_tce, "%Y-%m-%d")
                except:
                    pass
        
        # Score calculado
        score_calculado = score_data.get("score") if score_data else None
        
        # Crear snapshot
        snapshot = CompanySnapshot(
            ruc=ruc,
            snapshot_date=datetime.utcnow(),
            
            # SUNAT
            sunat_status=sunat_status,
            sunat_debt=sunat_debt,
            sunat_num_trabajadores=sunat_num_trabajadores,
            sunat_ultimo_pago=sunat_ultimo_pago,
            
            # OSCE
            osce_inhabilitado=osce_inhabilitado,
            osce_sanciones_count=osce_sanciones_count,
            osce_sanciones_vigentes=osce_sanciones_vigentes,
            osce_sanciones_historicas=osce_sanciones_historicas,
            osce_ultima_sancion_fecha=osce_ultima_sancion_fecha,
            
            # TCE
            tce_sanciones_count=tce_sanciones_count,
            tce_ultima_sancion_fecha=tce_ultima_sancion_fecha,
            
            # Features calculadas
            dias_ultimo_pago=dias_ultimo_pago,
            dias_ultima_sancion_osce=dias_ultima_sancion_osce,
            score_calculado=score_calculado,
            
            # Metadata
            source_api=source_api,
            query_id=query_id,
            raw_data_hash=raw_data_hash
        )
        
        self.db.add(snapshot)
        self.db.commit()
        self.db.refresh(snapshot)
        
        return snapshot
    
    def get_snapshots_by_ruc(
        self,
        ruc: str,
        days: int = 90
    ) -> list:
        """
        Obtiene los últimos N días de snapshots de una empresa.
        
        Args:
            ruc: RUC de la empresa
            days: Número de días hacia atrás
            
        Returns:
            Lista de snapshots ordenados por fecha
        """
        from_date = datetime.utcnow() - timedelta(days=days)
        
        return self.db.query(CompanySnapshot).filter(
            CompanySnapshot.ruc == ruc,
            CompanySnapshot.snapshot_date >= from_date
        ).order_by(CompanySnapshot.snapshot_date.desc()).all()
    
    def detect_changes(
        self,
        ruc: str,
        current_snapshot: CompanySnapshot
    ) -> list:
        """
        Detecta cambios significativos respecto al snapshot anterior.
        
        Returns:
            Lista de cambios detectados
        """
        changes = []
        
        # Obtener snapshot anterior
        previous = self.db.query(CompanySnapshot).filter(
            CompanySnapshot.ruc == ruc,
            CompanySnapshot.id != current_snapshot.id
        ).order_by(CompanySnapshot.snapshot_date.desc()).first()
        
        if not previous:
            return changes  # Primera consulta, no hay cambios
        
        # Detectar cambios críticos
        if not previous.osce_inhabilitado and current_snapshot.osce_inhabilitado:
            changes.append({
                "type": "osce_inhabilitado",
                "severity": "critical",
                "previous": "Habilitado",
                "current": "Inhabilitado"
            })
        
        if previous.osce_sanciones_vigentes == 0 and current_snapshot.osce_sanciones_vigentes > 0:
            changes.append({
                "type": "osce_nueva_sancion",
                "severity": "high",
                "previous": f"{previous.osce_sanciones_vigentes} sanciones",
                "current": f"{current_snapshot.osce_sanciones_vigentes} sanciones"
            })
        
        if previous.sunat_debt == 0 and current_snapshot.sunat_debt > 0:
            changes.append({
                "type": "sunat_nueva_deuda",
                "severity": "medium",
                "previous": "Sin deuda",
                "current": f"Deuda: S/ {current_snapshot.sunat_debt:,.2f}"
            })
        
        return changes


class AlertService:
    """
    Servicio para crear y enviar alertas a usuarios cuando
    sus proveedores cambian de estado.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_alert(
        self,
        user_id: str,
        supplier_ruc: str,
        supplier_name: str,
        change_type: str,
        previous_status: str,
        new_status: str,
        severity: str = "medium"
    ) -> SupplierAlert:
        """
        Crea una alerta para un usuario sobre un cambio en su proveedor.
        """
        alert = SupplierAlert(
            user_id=user_id,
            supplier_ruc=supplier_ruc,
            supplier_name=supplier_name,
            change_type=change_type,
            previous_status=previous_status,
            new_status=new_status,
            severity=severity
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        # Enviar email si es high/critical
        if severity in ['high', 'critical']:
            try:
                user = self.db.query(User).filter(User.id == user_id).first()
                if user and user.email:
                    email_service.send_supplier_alert_email(
                        to_email=user.email,
                        company_name=user.company_name or user.full_name or "Empresa",
                        supplier_ruc=supplier_ruc,
                        supplier_name=supplier_name,
                        change_type=change_type,
                        previous_status=previous_status,
                        new_status=new_status,
                        severity=severity
                    )
            except Exception as e:
                print(f"[AlertService] Error enviando email de alerta: {e}")
        
        return alert
    
    def get_unread_alerts(self, user_id: str) -> list:
        """Obtiene alertas no leídas de un usuario."""
        return self.db.query(SupplierAlert).filter(
            SupplierAlert.user_id == user_id,
            SupplierAlert.is_read == False
        ).order_by(SupplierAlert.created_at.desc()).all()


# Funciones helper para usar en routers

def save_company_snapshot(
    db: Session,
    ruc: str,
    verification_data: Dict[str, Any],
    query_id: Optional[str] = None
) -> CompanySnapshot:
    """
    Guarda un snapshot desde los datos de una verificación.
    
    Esta función se llama automáticamente al final de cada verificación.
    """
    service = SnapshotService(db)
    
    # Extraer datos de las diferentes fuentes
    sunat_data = verification_data.get("sunat", {})
    osce_data = verification_data.get("osce", {})
    tce_data = verification_data.get("tce", {})
    score_data = {
        "score": verification_data.get("score"),
        "contributions": verification_data.get("contributions", {})
    }
    
    snapshot = service.save_snapshot(
        ruc=ruc,
        sunat_data=sunat_data,
        osce_data=osce_data,
        tce_data=tce_data,
        score_data=score_data,
        source_api="decolecta",
        query_id=query_id
    )
    
    # Detectar cambios y crear alertas si es necesario
    changes = service.detect_changes(ruc, snapshot)
    
    return snapshot
