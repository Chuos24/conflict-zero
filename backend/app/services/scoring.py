import math
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.core.config import get_settings

settings = get_settings()

class ScoringEngine:
    """
    Motor de scoring predictivo para verificación de RUCs.
    Calcula una puntuación de 0-100 basada en:
    - 30% Deuda SUNAT
    - 40% Sanciones OSCE
    - 30% ML predictivo (anomalías)
    """
    
    def __init__(self):
        self.sunat_weight = settings.SCORE_SUNAT_WEIGHT
        self.osce_weight = settings.SCORE_OSCE_WEIGHT
        self.ml_weight = settings.SCORE_ML_WEIGHT
    
    def calculate_sunat_score(self, debt_amount: float) -> float:
        """
        Calcula el score basado en deuda SUNAT usando escala logarítmica.
        
        Score alto (riesgo bajo) = menos deuda
        Score bajo (riesgo alto) = más deuda
        
        Args:
            debt_amount: Monto de deuda en soles
            
        Returns:
            Score entre 0-100
        """
        if debt_amount <= 0:
            return 100.0
        
        # Escala logarítmica para normalizar montos
        # Deuda de 10k → score ~80
        # Deuda de 100k → score ~60
        # Deuda de 1M → score ~40
        # Deuda de 10M+ → score ~10
        
        log_debt = math.log10(debt_amount + 1)
        max_log = math.log10(100_000_000)  # 100M como máximo referencia
        
        normalized = 1 - (min(log_debt, max_log) / max_log)
        score = normalized * 100
        
        return max(0, min(100, score))
    
    def calculate_osce_score(self, sanctions: List[Dict[str, Any]]) -> float:
        """
        Calcula el score basado en sanciones OSCE.
        
        - Sin sanciones: 100
        - 1 sanción leve: 60
        - 1 sanción grave: 20
        - Múltiples sanciones: 0-10
        
        Args:
            sanctions: Lista de sanciones OSCE
            
        Returns:
            Score entre 0-100
        """
        if not sanctions:
            return 100.0
        
        # Clasificar sanciones
        severe_count = sum(1 for s in sanctions if s.get('severity') == 'grave')
        minor_count = sum(1 for s in sanctions if s.get('severity') != 'grave')
        
        if severe_count > 0:
            return max(0, 20 - (severe_count * 10))
        
        if minor_count > 0:
            return max(30, 60 - (minor_count * 15))
        
        return 100.0
    
    def calculate_tce_score(self, sanctions: List[Dict[str, Any]]) -> float:
        """
        Calcula el score basado en sanciones TCE (Tribunal de Contrataciones).
        Similar a OSCE pero con peso menor.
        
        Args:
            sanctions: Lista de sanciones TCE
            
        Returns:
            Score entre 0-100
        """
        if not sanctions:
            return 100.0
        
        severe_count = sum(1 for s in sanctions if s.get('type') == 'inhabilitacion')
        minor_count = len(sanctions) - severe_count
        
        if severe_count > 0:
            return max(10, 40 - (severe_count * 15))
        
        if minor_count > 0:
            return max(50, 80 - (minor_count * 10))
        
        return 100.0
    
    def calculate_ml_score(self, ruc: str, sunat_data: Dict, osce_data: List, 
                           tce_data: List) -> Tuple[float, List[str], float]:
        """
        Simula análisis ML para detección de anomalías.
        En producción, esto usaría un modelo entrenado.
        
        Detecta:
        - Cambios bruscos en deuda
        - Patrones de sanciones recurrentes
        - Inconsistencias en datos
        - Riesgo sectorial
        
        Returns:
            (score, risk_factors, confidence)
        """
        risk_factors = []
        anomaly_indicators = 0
        
        # Factor 1: RUC reciente (primeros 2 dígitos indican año)
        try:
            ruc_year = int(ruc[:2])
            if ruc_year > 20:  # RUCs recientes (2020+)
                risk_factors.append("Empresa constituida recientemente")
                anomaly_indicators += 1
        except:
            pass
        
        # Factor 2: Deuda creciente (simulado)
        if sunat_data.get('debt_amount', 0) > 100000:
            risk_factors.append("Alto nivel de deuda tributaria")
            anomaly_indicators += 2
        
        # Factor 3: Sanciones múltiples
        total_sanctions = len(osce_data) + len(tce_data)
        if total_sanctions >= 3:
            risk_factors.append("Historial recurrente de sanciones")
            anomaly_indicators += 3
        elif total_sanctions > 0:
            risk_factors.append("Sanciones previas detectadas")
            anomaly_indicators += 1
        
        # Factor 4: Sector de riesgo (basado en RUC)
        high_risk_sectors = ['20', '45', '46', '47']  # Construcción, comercio
        sector_code = ruc[2:4] if len(ruc) >= 4 else ''
        if sector_code in high_risk_sectors:
            risk_factors.append("Sector con histórico de incumplimiento")
            anomaly_indicators += 1
        
        # Calcular score (más anomalías = menor score)
        base_score = 100 - (anomaly_indicators * 15)
        score = max(0, min(100, base_score))
        
        # Confidence basado en cantidad de datos disponibles
        confidence = min(0.95, 0.5 + (total_sanctions * 0.1))
        
        return score, risk_factors, confidence
    
    def calculate_total_score(
        self,
        ruc: str,
        sunat_debt: float,
        osce_sanctions: List[Dict[str, Any]],
        tce_sanctions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Calcula el score total ponderado.
        
        Returns:
            Dict con score total, contribuciones individuales y nivel de riesgo
        """
        # Calcular scores individuales
        sunat_score = self.calculate_sunat_score(sunat_debt)
        osce_score = self.calculate_osce_score(osce_sanctions)
        tce_score = self.calculate_tce_score(tce_sanctions)
        ml_score, ml_factors, ml_confidence = self.calculate_ml_score(
            ruc, {'debt_amount': sunat_debt}, osce_sanctions, tce_sanctions
        )
        
        # OSCE y TCE se combinan (OSCE tiene más peso en contrataciones públicas)
        combined_regulatory_score = (osce_score * 0.7) + (tce_score * 0.3)
        
        # Calcular score ponderado final
        weighted_score = (
            (sunat_score * self.sunat_weight) +
            (combined_regulatory_score * self.osce_weight) +
            (ml_score * self.ml_weight)
        )
        
        # Redondear a entero
        final_score = int(round(weighted_score))
        
        # Determinar nivel de riesgo
        if final_score >= 80:
            risk_level = "low"
        elif final_score >= 60:
            risk_level = "medium"
        elif final_score >= 40:
            risk_level = "high"
        else:
            risk_level = "critical"
        
        return {
            "total_score": final_score,
            "risk_level": risk_level,
            "breakdown": {
                "sunat_contribution": round(sunat_score * self.sunat_weight, 2),
                "osce_contribution": round(osce_score * self.osce_weight, 2),
                "tce_contribution": round(tce_score * self.osce_weight * 0.3, 2),
                "ml_contribution": round(ml_score * self.ml_weight, 2),
            },
            "individual_scores": {
                "sunat": round(sunat_score, 2),
                "osce": round(osce_score, 2),
                "tce": round(tce_score, 2),
                "ml": round(ml_score, 2),
            },
            "ml_analysis": {
                "anomaly_score": round(100 - ml_score, 2),
                "risk_factors": ml_factors,
                "confidence": round(ml_confidence, 2)
            }
        }
    
    def get_risk_description(self, risk_level: str) -> str:
        """Retorna descripción del nivel de riesgo."""
        descriptions = {
            "low": "Riesgo bajo. Empresa con buen historial de cumplimiento normativo.",
            "medium": "Riesgo moderado. Se recomienda revisión adicional antes de contratar.",
            "high": "Riesgo alto. Se detectaron incumplimientos significativos.",
            "critical": "Riesgo crítico. Múltiples sanciones graves. No recomendado."
        }
        return descriptions.get(risk_level, "Nivel de riesgo desconocido")

# Instancia global
scoring_engine = ScoringEngine()
