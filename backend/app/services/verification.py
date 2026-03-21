from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import VerificationRequest as VerificationModel, User
from app.services.scoring import scoring_engine
from app.services.external_api import external_api
from app.core.cache import cache

class VerificationService:
    """
    Servicio principal para realizar verificaciones de RUC.
    Combina consulta a APIs externas, cálculo de score y persistencia.
    """
    
    def verify_ruc(
        self,
        ruc: str,
        user: Optional[User] = None,
        db: Optional[Session] = None,
        skip_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Realiza una verificación completa de un RUC.
        
        Args:
            ruc: Número de RUC (11 dígitos)
            user: Usuario que realiza la consulta (opcional)
            db: Sesión de base de datos (opcional)
            skip_cache: Si es True, ignora el caché
            
        Returns:
            Dict con todos los datos de la verificación
            
        Raises:
            ValueError: Si el RUC es inválido
            HTTPException: Si no hay APIs configuradas para datos reales
        """
        # Validar RUC
        if not ruc or len(ruc) != 11 or not ruc.isdigit():
            raise ValueError("RUC inválido. Debe tener 11 dígitos numéricos.")
        
        # Verificar caché
        cache_key = f"verification:{ruc}"
        if not skip_cache:
            cached_result = cache.get(cache_key)
            if cached_result:
                cached_result["cached"] = True
                return cached_result
        
        # Obtener datos externos
        external_data = external_api.get_full_ruc_data(ruc)
        
        # Verificar si hay error en datos externos
        if external_data.get("error"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=external_data.get("message", "Error al obtener datos del RUC")
            )
        
        # Calcular score
        score_result = scoring_engine.calculate_total_score(
            ruc=ruc,
            sunat_debt=external_data["sunat"].get("deuda_coactiva", 0),
            osce_sanctions=external_data["osce_sanctions"],
            tce_sanctions=external_data["tce_sanctions"]
        )
        
        # Construir respuesta
        result = {
            "ruc": ruc,
            "company_name": external_data["company_name"],
            "score": score_result["total_score"],
            "risk_level": score_result["risk_level"],
            
            # Datos SUNAT reales
            "sunat_data": {
                "debt_amount": external_data["sunat"].get("deuda_coactiva", 0),
                "tax_status": external_data["sunat"].get("estado_tributario", ""),
                "contributor_status": external_data["sunat"].get("estado_contribuyente", ""),
                "address": external_data["sunat"].get("direccion", ""),
                "department": external_data["sunat"].get("departamento", ""),
                "province": external_data["sunat"].get("provincia", ""),
                "district": external_data["sunat"].get("distrito", ""),
                "ubigeo": external_data["sunat"].get("ubigeo", ""),
                "last_updated": external_data["sunat"].get("fecha_consulta"),
                "data_source": external_data["sunat"].get("fuente", "desconocido")
            },
            
            # Sanciones OSCE
            "osce_sanctions": [
                {
                    "sanction_id": s.get("sanction_id", ""),
                    "description": s.get("description", ""),
                    "date": s.get("date"),
                    "status": s.get("status", ""),
                    "severity": s.get("severity", ""),
                    "entity": s.get("entity", "OSCE")
                }
                for s in external_data["osce_sanctions"]
            ],
            
            # Sanciones TCE
            "tce_sanctions": [
                {
                    "sanction_id": s.get("sanction_id", ""),
                    "description": s.get("description", ""),
                    "date": s.get("date"),
                    "status": s.get("status", ""),
                    "type": s.get("type", ""),
                    "entity": s.get("entity", "TCE")
                }
                for s in external_data["tce_sanctions"]
            ],
            
            # Análisis ML
            "ml_analysis": {
                "anomaly_score": score_result["ml_analysis"]["anomaly_score"],
                "risk_factors": score_result["ml_analysis"]["risk_factors"],
                "confidence": score_result["ml_analysis"]["confidence"]
            },
            
            # Desglose del score
            "score_breakdown": {
                "sunat_contribution": score_result["breakdown"]["sunat_contribution"],
                "osce_contribution": score_result["breakdown"]["osce_contribution"],
                "tce_contribution": score_result["breakdown"]["tce_contribution"],
                "ml_contribution": score_result["breakdown"]["ml_contribution"],
                "total_score": score_result["total_score"]
            },
            
            # Metadata
            "verification_date": datetime.now().isoformat(),
            "cached": False,
            "pdf_url": None,  # Generado asíncronamente si se solicita
            "real_data": True,
            "data_sources": external_data.get("data_sources", [])
        }
        
        # Guardar en caché (1 hora)
        cache.set(cache_key, result, expire=3600)
        
        # Persistir en base de datos si hay usuario
        if user and db:
            self._save_verification(user, result, db)
        
        return result
    
    def _save_verification(
        self,
        user: User,
        result: Dict[str, Any],
        db: Session
    ) -> None:
        """Guarda la verificación en la base de datos."""
        verification = VerificationModel(
            user_id=user.id,
            ruc=result["ruc"],
            company_name=result.get("company_name"),
            score=result["score"],
            risk_level=result["risk_level"],
            
            # SUNAT
            sunat_debt=result["sunat_data"]["debt_amount"],
            sunat_score_contribution=result["score_breakdown"]["sunat_contribution"],
            
            # OSCE
            osce_sanctions_count=len(result["osce_sanctions"]),
            osce_score_contribution=result["score_breakdown"]["osce_contribution"],
            osce_sanctions_details=result["osce_sanctions"],
            
            # TCE
            tce_sanctions_count=len(result["tce_sanctions"]),
            tce_score_contribution=result["score_breakdown"]["tce_contribution"],
            tce_sanctions_details=result["tce_sanctions"],
            
            # ML
            ml_anomaly_score=result["ml_analysis"]["anomaly_score"],
            ml_score_contribution=result["score_breakdown"]["ml_contribution"],
            
            # Raw data
            raw_data=result
        )
        
        db.add(verification)
        db.commit()
        db.refresh(verification)
        
        # Actualizar contador del usuario
        user.monthly_requests += 1
        db.commit()
    
    def get_verification_history(
        self,
        user: User,
        db: Session,
        limit: int = 50
    ):
        """Obtiene el historial de verificaciones de un usuario."""
        from app.models import VerificationRequest as VR
        
        return db.query(VR).filter(
            VR.user_id == user.id
        ).order_by(
            VR.created_at.desc()
        ).limit(limit).all()

# Instancia global
verification_service = VerificationService()
