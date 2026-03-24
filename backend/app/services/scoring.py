import math
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.core.config import get_settings

settings = get_settings()

class ScoringEngine:
    """
    Motor de scoring predictivo para verificación de RUCs.
    Calcula una puntuación de 0-100 basada en datos SUNAT y análisis predictivo.
    
    Fórmula actual (sin acceso a sanciones OSCE por WAF):
    - 40% Estado SUNAT (Activo/Baja/Suspensión)
    - 30% Condición domicilio (Habido/No habido)
    - 20% Antigüedad del RUC
    - 10% Análisis predictivo (sector, nombre)
    """
    
    def __init__(self):
        # Pesos ajustados sin acceso a OSCE
        self.sunat_estado_weight = 0.40
        self.sunat_condicion_weight = 0.30
        self.antiguedad_weight = 0.20
        self.ml_weight = 0.10
    
    def _extract_ruc_year(self, ruc: str) -> int:
        """Extrae el año de constitución del RUC (primeros 2 dígitos)."""
        try:
            if len(ruc) >= 2:
                year_code = int(ruc[:2])
                # RUCs antes del 2000 usan código diferente
                if year_code < 50:
                    return 2000 + year_code
                else:
                    return 1900 + year_code
        except (ValueError, IndexError):
            pass
        return 2000  # Default
    
    def calculate_antiguedad_score(self, ruc: str) -> Tuple[float, int]:
        """
        Calcula score basado en antigüedad del RUC.
        
        Args:
            ruc: Número de RUC
            
        Returns:
            (score, años_de_antiguedad)
        """
        year_constitucion = self._extract_ruc_year(ruc)
        current_year = datetime.now().year
        antiguedad = max(0, current_year - year_constitucion)
        
        # Score basado en antigüedad
        if antiguedad >= 10:
            score = 100.0
        elif antiguedad >= 5:
            score = 85.0
        elif antiguedad >= 2:
            score = 70.0
        elif antiguedad >= 1:
            score = 60.0
        else:
            score = 40.0  # RUC muy nuevo
        
        return score, antiguedad
    
    def calculate_estado_score(self, estado: str) -> float:
        """
        Calcula score basado en estado del contribuyente.
        
        Args:
            estado: Estado del contribuyente (ACTIVO, BAJA, SUSPENSION, etc.)
            
        Returns:
            Score entre 0-100
        """
        estado = (estado or "").upper().strip()
        
        if estado == "ACTIVO":
            return 100.0
        elif estado == "BAJA DE OFICIO" or estado == "BAJA":
            return 0.0
        elif estado == "SUSPENSION TEMPORAL":
            return 30.0
        elif estado == "SUSPENSION DEFINITIVA":
            return 10.0
        else:
            return 50.0  # Estado desconocido = riesgo medio
    
    def calculate_condicion_score(self, condicion: str) -> float:
        """
        Calcula score basado en condición del domicilio.
        
        Args:
            condicion: Condición del domicilio (HABIDO, NO HABIDO, etc.)
            
        Returns:
            Score entre 0-100
        """
        condicion = (condicion or "").upper().strip()
        
        if condicion == "HABIDO":
            return 100.0
        elif "NO HABIDO" in condicion:
            return 0.0
        elif "NO ENCONTRADO" in condicion:
            return 20.0
        elif "PENDIENTE" in condicion:
            return 50.0
        else:
            return 70.0  # Condición desconocida
    
    def calculate_sunat_score(self, estado: str, condicion: str, deuda: float = 0) -> Dict[str, float]:
        """
        Calcula score compuesto de SUNAT basado en estado + condición + deuda.
        
        Returns:
            Dict con scores individuales y ponderados
        """
        estado_score = self.calculate_estado_score(estado)
        condicion_score = self.calculate_condicion_score(condicion)
        
        # Score de deuda (si está disponible)
        if deuda > 0:
            log_debt = math.log10(deuda + 1)
            max_log = math.log10(100_000_000)
            debt_score = max(0, 100 - (log_debt / max_log) * 100)
        else:
            debt_score = 100.0
        
        return {
            "estado_score": estado_score,
            "condicion_score": condicion_score,
            "debt_score": debt_score,
            "estado_contrib": self.sunat_estado_weight,
            "condicion_contrib": self.sunat_condicion_weight
        }
    
    def calculate_ml_score(self, ruc: str, razon_social: str, 
                           estado: str, condicion: str) -> Tuple[float, List[str], float]:
        """
        Análisis predictivo para detección de anomalías.
        
        Detecta:
        - Empresas constituidas recientemente
        - Sectores de riesgo
        - Nombres sospechosos (genéricos, números, etc.)
        - Estado/condición problemáticas
        
        Returns:
            (score, risk_factors, confidence)
        """
        risk_factors = []
        risk_points = 0
        
        razon_social = (razon_social or "").upper()
        
        # Factor 1: Antigüedad
        year_constitucion = self._extract_ruc_year(ruc)
        antiguedad = datetime.now().year - year_constitucion
        
        if antiguedad < 1:
            risk_factors.append("Empresa constituida hace menos de 1 año")
            risk_points += 2
        elif antiguedad < 2:
            risk_factors.append("Empresa constituida recientemente")
            risk_points += 1
        
        # Factor 2: Estado problemático
        if estado.upper() not in ["ACTIVO", "HABIDO"]:
            risk_factors.append(f"Estado contribuyente: {estado}")
            risk_points += 3
        
        # Factor 3: Condición problemática
        if "NO HABIDO" in condicion.upper():
            risk_factors.append("Contribuyente no habido")
            risk_points += 4
        elif "NO ENCONTRADO" in condicion.upper():
            risk_factors.append("Domicilio no encontrado")
            risk_points += 3
        
        # Factor 4: Sector de riesgo (basado en RUC)
        # Los dígitos 3-4 del RUC indican el tipo de empresa
        if len(ruc) >= 4:
            tipo = ruc[2:4]
            high_risk = ['15', '20', '45', '46', '47', '56']  # Temporales, construcción, comercio, etc.
            medium_risk = ['10', '11', '12', '13', '14']  # Diversos
            
            if tipo in high_risk:
                risk_factors.append("Sector con histórico de incumplimiento")
                risk_points += 2
            elif tipo in medium_risk:
                risk_points += 1
        
        # Factor 5: Nombre genérico o sospechoso
        generic_terms = ['CONSULTING', 'CONSULTORA', 'SERVICES', 'GROUP', 'SAC', 'EIRL', 'SRL']
        suspicious_patterns = ['XXXX', 'AAAA', '1234', '0000']
        
        # Contar cuántos términos genéricos tiene el nombre
        generic_count = sum(1 for term in generic_terms if term in razon_social)
        if generic_count >= 3:
            risk_factors.append("Nombre comercial muy genérico")
            risk_points += 1
        
        # Verificar patrones sospechosos
        for pattern in suspicious_patterns:
            if pattern in razon_social:
                risk_factors.append("Patrón sospechoso en nombre comercial")
                risk_points += 2
                break
        
        # Calcular score final (más risk_points = menor score)
        base_score = 100 - (risk_points * 8)
        score = max(0, min(100, base_score))
        
        # Confidence basado en cantidad de factores analizados
        confidence = min(0.9, 0.6 + (len(risk_factors) * 0.05))
        
        return score, risk_factors, confidence
    
    def calculate_total_score(
        self,
        ruc: str,
        razon_social: str,
        estado: str,
        condicion: str,
        deuda: float = 0,
        osce_sanctions: List[Dict[str, Any]] = None,
        tce_sanctions: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calcula el score total ponderado.
        
        Args:
            ruc: Número de RUC
            razon_social: Razón social
            estado: Estado del contribuyente
            condicion: Condición del domicilio
            deuda: Monto de deuda SUNAT (opcional)
            osce_sanctions: Lista de sanciones OSCE (opcional)
            tce_sanctions: Lista de sanciones TCE (opcional)
        
        Returns:
            Dict con score total, contribuciones individuales y nivel de riesgo
        """
        # Calcular scores individuales
        sunat_data = self.calculate_sunat_score(estado, condicion, deuda)
        antiguedad_score, antiguedad_years = self.calculate_antiguedad_score(ruc)
        ml_score, ml_factors, ml_confidence = self.calculate_ml_score(ruc, razon_social, estado, condicion)
        
        # Ponderar contribuciones SUNAT
        sunat_contribution = (
            sunat_data["estado_score"] * 0.6 +
            sunat_data["condicion_score"] * 0.4
        ) * (self.sunat_estado_weight + self.sunat_condicion_weight)
        
        # Calcular score ponderado final
        weighted_score = (
            sunat_contribution +
            (antiguedad_score * self.antiguedad_weight) +
            (ml_score * self.ml_weight)
        )
        
        # Ajustar por sanciones si están disponibles (rara vez)
        if osce_sanctions and len(osce_sanctions) > 0:
            weighted_score *= 0.5  # Penalización severa
            ml_factors.append(f"{len(osce_sanctions)} sanción(es) OSCE detectada(s)")
        
        if tce_sanctions and len(tce_sanctions) > 0:
            weighted_score *= 0.7  # Penalización moderada
            ml_factors.append(f"{len(tce_sanctions)} sanción(es) TCE detectada(s)")
        
        # Redondear a entero
        final_score = int(round(weighted_score))
        final_score = max(0, min(100, final_score))
        
        # Determinar nivel de riesgo
        if final_score >= 80:
            risk_level = "low"
            risk_emoji = "🟢"
        elif final_score >= 60:
            risk_level = "medium"
            risk_emoji = "🟡"
        elif final_score >= 40:
            risk_level = "high"
            risk_emoji = "🟠"
        else:
            risk_level = "critical"
            risk_emoji = "🔴"
        
        return {
            "total_score": final_score,
            "risk_level": risk_level,
            "risk_emoji": risk_emoji,
            "breakdown": {
                "sunat_contribution": round(sunat_contribution, 2),
                "antiguedad_contribution": round(antiguedad_score * self.antiguedad_weight, 2),
                "ml_contribution": round(ml_score * self.ml_weight, 2),
            },
            "individual_scores": {
                "sunat_estado": round(sunat_data["estado_score"], 2),
                "sunat_condicion": round(sunat_data["condicion_score"], 2),
                "sunat_deuda": round(sunat_data["debt_score"], 2),
                "antiguedad": round(antiguedad_score, 2),
                "antiguedad_years": antiguedad_years,
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
            "low": "Riesgo bajo. Empresa con buen perfil de cumplimiento.",
            "medium": "Riesgo moderado. Se recomienda revisión adicional.",
            "high": "Riesgo alto. Detectadas irregularidades significativas.",
            "critical": "Riesgo crítico. No recomendado para contratación."
        }
        return descriptions.get(risk_level, "Nivel de riesgo desconocido")

# Instancia global
scoring_engine = ScoringEngine()
