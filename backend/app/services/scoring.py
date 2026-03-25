import math
import random
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.core.config import get_settings
from app.core.database import get_db

settings = get_settings()

class ScoringEngine:
    """
    Motor de scoring predictivo para verificación de RUCs.
    Calcula una puntuación de 0-100 basada en:
    - 30% Estado SUNAT (Activo/Baja/Suspensión)
    - 25% Condición domicilio (Habido/No habido)
    - 20% Antigüedad del RUC
    - 15% Sanciones OSCE/Penalidades (desde PostgreSQL)
    - 10% Análisis predictivo (sector, nombre)
    """

    def __init__(self):
        # Pesos actualizados con datos OSCE reales
        self.sunat_estado_weight = 0.30
        self.sunat_condicion_weight = 0.25
        self.antiguedad_weight = 0.20
        self.osce_weight = 0.15
        self.ml_weight = 0.10

    def get_osce_data_from_db(self, ruc: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene datos de riesgo OSCE desde PostgreSQL.

        Returns:
            Dict con datos de la tabla osce_risk_data o None si no existe
        """
        try:
            from sqlalchemy import text
            from app.core.database import SessionLocal

            db = SessionLocal()
            try:
                result = db.execute(
                    text("SELECT * FROM osce_risk_data WHERE ruc = :ruc"),
                    {"ruc": ruc}
                ).fetchone()

                if result:
                    return {
                        'ruc': result.ruc,
                        'score_osce_anual': result.score_osce_anual,
                        'flag_sancion_tce': result.flag_sancion_tce,
                        'flag_sancion_osce': result.flag_sancion_osce,
                        'cantidad_sanciones': result.cantidad_sanciones,
                        'cantidad_penalidades': result.cantidad_penalidades,
                        'sanciones_vigentes': result.sanciones_vigentes,
                        'inhabilitaciones_vigentes': result.inhabilitaciones_vigentes,
                        'dias_inhabilitacion_restantes': result.dias_inhabilitacion_restantes,
                        'monto_total_penalidades': float(result.monto_total_penalidades) if result.monto_total_penalidades else 0,
                        'fecha_sync': result.fecha_sync.isoformat() if result.fecha_sync else None,
                    }
                return None
            finally:
                db.close()
        except Exception as e:
            print(f"Error consultando OSCE DB: {e}")
            return None

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

    def calculate_sanciones_score(self, sanciones: List[Dict[str, Any]], ruc: str = None) -> Dict[str, Any]:
        """
        Calcula el score basado en sanciones OSCE reales.
        Si se proporciona RUC, consulta directamente la base de datos para obtener el score precalculado.

        Returns:
            Dict con score y detalle de sanciones
        """
        # Si tenemos RUC, consultar directamente la base de datos para score precalculado
        if ruc:
            try:
                from app.services.osce_datos_abiertos import osce_datos_abiertos
                db_data = osce_datos_abiertos.get_sanciones_from_db(ruc)
                if db_data:
                    total = db_data['cantidad_sanciones'] + db_data['cantidad_penalidades'] + db_data['cantidad_inhabilitaciones']
                    return {
                        "score": float(db_data['score_osce_anual']),
                        "cantidad": total,
                        "tiene_inhabilitaciones": db_data['cantidad_sanciones'] > 0,
                        "tiene_penalidades": db_data['cantidad_penalidades'] > 0,
                        "tiene_judiciales": db_data['cantidad_inhabilitaciones'] > 0,
                        "inhabilitaciones": db_data['cantidad_sanciones'],
                        "penalidades": db_data['cantidad_penalidades'],
                        "judiciales": db_data['cantidad_inhabilitaciones'],
                        "severidad": "grave" if db_data['cantidad_inhabilitaciones'] > 0 else "alta" if db_data['cantidad_sanciones'] > 0 else "media" if db_data['cantidad_penalidades'] > 0 else "ninguna",
                        "fuente": "postgresql"
                    }
            except Exception as e:
                print(f"[Scoring] Error consultando OSCE DB: {e}")

        # Fallback: calcular basado en lista de sanciones
        if not sanciones:
            return {
                "score": 100.0,
                "cantidad": 0,
                "tiene_inhabilitaciones": False,
                "tiene_penalidades": False,
                "severidad": "ninguna"
            }

        total = len(sanciones)
        inhabilitaciones = sum(1 for s in sanciones if s.get('tipo') == 'inhabilitacion')
        penalidades = sum(1 for s in sanciones if s.get('tipo') == 'penalidad')
        judiciales = sum(1 for s in sanciones if s.get('tipo') == 'inhabilitacion_judicial')

        # Calcular severidad
        if judiciales > 0:
            severidad = "grave"
            score = max(0, 30 - (judiciales * 10))
        elif inhabilitaciones > 0:
            severidad = "alta"
            score = max(20, 50 - (inhabilitaciones * 15))
        elif penalidades > 0:
            severidad = "media"
            score = max(40, 70 - (penalidades * 10))
        else:
            severidad = "baja"
            score = 80.0

        return {
            "score": score,
            "cantidad": total,
            "tiene_inhabilitaciones": inhabilitaciones > 0,
            "tiene_penalidades": penalidades > 0,
            "tiene_judiciales": judiciales > 0,
            "inhabilitaciones": inhabilitaciones,
            "penalidades": penalidades,
            "judiciales": judiciales,
            "severidad": severidad
        }

    def calculate_rnp_score(self, ruc: str) -> Dict[str, Any]:
        """
        Calcula score basado en datos RNP/TCE.
        Consulta la base de datos de sanciones del Registro Nacional de Proveedores.
        
        Scoring:
        - Definitiva + Vigente = Score 20 (crítico)
        - Temporal + Vigente = Score 40 (alto)
        - No vigente = Score 70 (histórico)
        - Sin sanciones = Score 100
        
        Returns:
            Dict con score y metadatos
        """
        try:
            from app.services.rnp_datos import rnp_service
            
            datos = rnp_service.get_sanciones_from_db(ruc)
            
            if not datos or datos.get('cantidad_sanciones', 0) == 0:
                return {
                    'score': 100,
                    'tiene_sanciones': False,
                    'cantidad': 0,
                    'sanciones_vigentes': 0,
                    'sanciones_definitivas': 0,
                    'sanciones_temporales': 0,
                    'monto_total_multas': 0,
                    'nivel_riesgo': 'low'
                }
            
            score = 100
            
            # Penalización por sanciones definitivas vigentes
            if datos.get('sanciones_definitivas', 0) > 0 and datos.get('sanciones_vigentes', 0) > 0:
                score = min(score, 20)
            # Penalización por sanciones temporales vigentes
            elif datos.get('sanciones_temporales', 0) > 0 and datos.get('sanciones_vigentes', 0) > 0:
                score = min(score, 40)
            # Sanciones históricas (no vigentes)
            elif datos.get('cantidad_sanciones', 0) > 0:
                score = min(score, 70)
            
            # Penalización adicional por monto de multas
            monto = datos.get('monto_total_multas', 0)
            if monto > 100000:
                score -= 10
            elif monto > 50000:
                score -= 5
            
            score = max(0, score)
            
            # Determinar nivel de riesgo
            if score <= 30:
                nivel = 'critical'
            elif score <= 50:
                nivel = 'high'
            elif score <= 70:
                nivel = 'medium'
            else:
                nivel = 'low'
            
            return {
                'score': score,
                'tiene_sanciones': True,
                'cantidad': datos.get('cantidad_sanciones', 0),
                'sanciones_vigentes': datos.get('sanciones_vigentes', 0),
                'sanciones_definitivas': datos.get('sanciones_definitivas', 0),
                'sanciones_temporales': datos.get('sanciones_temporales', 0),
                'monto_total_multas': monto,
                'nivel_riesgo': nivel,
                'fecha_maxima_vigencia': datos.get('fecha_maxima_vigencia')
            }
            
        except Exception as e:
            print(f"[Scoring] Error calculando score RNP: {e}")
            return {
                'score': 100,
                'tiene_sanciones': False,
                'cantidad': 0,
                'error': str(e)
            }

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

        # Calcular score de sanciones OSCE (datos reales desde PostgreSQL)
        osce_data = self.calculate_sanciones_score(osce_sanctions or [], ruc=ruc)
        osce_score = osce_data["score"]

        # ============================================================
        # INTEGRACIÓN RNP/TCE - Nueva fuente de datos
        # ============================================================
        # Calcular score de sanciones RNP (TCE desde RNP)
        rnp_data = self.calculate_rnp_score(ruc)
        rnp_score = rnp_data["score"]

        # Combinar OSCE y RNP - tomar el peor score (más conservador)
        combined_osce_rnp_score = min(osce_score, rnp_score)

        # Flags combinados
        has_judiciales = osce_data.get("tiene_judiciales", False) or rnp_data.get("sanciones_definitivas", 0) > 0
        has_inhabilitaciones = osce_data.get("tiene_inhabilitaciones", False) or rnp_data.get("sanciones_vigentes", 0) > 0
        has_penalidades = osce_data.get("tiene_penalidades", False) or rnp_data.get("monto_total_multas", 0) > 0

        # ============================================================
        # SCORING CRUDO PARA COMPLIANCE - SANCIONES PESAN MÁS
        # ============================================================
        # Si tiene sanciones graves, SUNAT limpio no "rescata" el score

        # Score base ponderado (el cálculo original)
        base_weighted_score = (
            (sunat_data["estado_score"] * self.sunat_estado_weight) +
            (sunat_data["condicion_score"] * self.sunat_condicion_weight) +
            (antiguedad_score * self.antiguedad_weight) +
            (combined_osce_rnp_score * self.osce_weight) +
            (ml_score * self.ml_weight)
        )

        # Aplicar CAP según gravedad de sanciones (SCORING CRUDO)
        # Prioridad: RNP Definitiva > OSCE Judicial > OSCE Inhabilitación > Temporal
        if rnp_data.get("sanciones_definitivas", 0) > 0 and rnp_data.get("sanciones_vigentes", 0) > 0:
            # Sanción definitiva vigente desde RNP = MÁXIMO 20 (riesgo crítico máximo)
            max_score = 20
            compliance_note = "⛔ Sanción DEFINITIVA vigente (RNP-TCE) - PROHIBIDO contratar"
        elif has_judiciales:
            # Inhabilitación judicial = MÁXIMO 30 (riesgo crítico)
            max_score = 30
            compliance_note = "⚠️ Inhabilitación judicial vigente - Riesgo crítico para contratación"
        elif has_inhabilitaciones:
            # Sanción OSCE con inhabilitación = MÁXIMO 50 (riesgo alto)
            max_score = 50
            compliance_note = "⚠️ Sanción con inhabilitación vigente - Riesgo significativo"
        elif rnp_data.get("sanciones_temporales", 0) > 0 and rnp_data.get("sanciones_vigentes", 0) > 0:
            # Sanción temporal vigente = MÁXIMO 40
            max_score = 40
            compliance_note = "⚠️ Sanción TEMPORAL vigente (RNP-TCE) - Revisión obligatoria"
        elif has_penalidades:
            # Solo penalidades = MÁXIMO 70 (riesgo moderado)
            max_score = 70
            compliance_note = "ℹ️ Penalidades/multas en contratos - Revisión requerida"
        else:
            # Limpio de sanciones = sin límite
            max_score = 100
            compliance_note = None

        # Aplicar el CAP (el score ponderado no puede superar el máximo permitido)
        final_score = min(base_weighted_score, max_score)

        # ============================================================
        # REINCIDENCIA ESCALADA - Patrón de comportamiento
        # ============================================================
        # Suma OSCE + RNP para medir reincidencia total
        cantidad_osce = osce_data.get("cantidad", 0)
        cantidad_rnp = rnp_data.get("cantidad_sanciones", 0)
        cantidad_total = cantidad_osce + cantidad_rnp
        
        reincidencia_penalty = 0
        reincidencia_nivel = None
        
        if cantidad_total >= 8:
            # Reincidente crónico: 8+ sanciones
            reincidencia_penalty = 30
            reincidencia_nivel = "crónico"
        elif cantidad_total >= 5:
            # Reincidente severo: 5-7 sanciones
            reincidencia_penalty = 20
            reincidencia_nivel = "severo"
        elif cantidad_total >= 3:
            # Reincidente: 3-4 sanciones
            reincidencia_penalty = 10
            reincidencia_nivel = "reincidente"
        elif cantidad_total > 1:
            # Múltiple: 2 sanciones
            reincidencia_penalty = 5
            reincidencia_nivel = "múltiple"
        
        if reincidencia_penalty > 0:
            final_score -= reincidencia_penalty

        # Asegurar límites
        final_score = max(0, min(100, final_score))
        final_score = int(round(final_score))

        # ============================================================

        # Agregar factores de riesgo de sanciones al análisis ML
        if osce_data["cantidad"] > 0:
            if has_judiciales:
                ml_factors.append(f"⚠️ {osce_data['judiciales']} inhabilitación(es) judicial(es) - GRAVÍSIMO")
            if has_inhabilitaciones:
                ml_factors.append(f"⚠️ {osce_data['inhabilitaciones']} sanción(es) OSCE con inhabilitación")
            if has_penalidades:
                ml_factors.append(f"⚠️ {osce_data['penalidades']} penalidad(es) en contratos")

        # Agregar factores de RNP si existen
        if rnp_data.get('tiene_sanciones'):
            if rnp_data.get('sanciones_definitivas', 0) > 0:
                ml_factors.append(f"⛔ {rnp_data['sanciones_definitivas']} sanción(es) DEFINITIVA(S) RNP-TCE")
            if rnp_data.get('sanciones_temporales', 0) > 0:
                ml_factors.append(f"⚠️ {rnp_data['sanciones_temporales']} sanción(es) TEMPORAL(ES) RNP-TCE")
            if rnp_data.get('monto_total_multas', 0) > 0:
                ml_factors.append(f"💰 Multas TCE: S/ {rnp_data['monto_total_multas']:,.2f}")

        # Agregar nota de compliance si existe
        if compliance_note:
            ml_factors.insert(0, compliance_note)
        
        # Agregar factor de reincidencia si aplica
        if reincidencia_nivel:
            ml_factors.append(f"📊 Reincidencia {reincidencia_nivel}: {cantidad_total} sanciones totales (-{reincidencia_penalty} pts)")

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
            "scoring_mode": "compliance_strict_v2",  # Versión con RNP
            "compliance_cap": max_score if max_score < 100 else None,
            "compliance_note": compliance_note,
            "base_score": round(base_weighted_score, 2),
            "fuentes_consultadas": ["SUNAT", "OSCE", "RNP-TCE"],
            "breakdown": {
                "sunat_estado_contribution": round(sunat_data["estado_score"] * self.sunat_estado_weight, 2),
                "sunat_condicion_contribution": round(sunat_data["condicion_score"] * self.sunat_condicion_weight, 2),
                "antiguedad_contribution": round(antiguedad_score * self.antiguedad_weight, 2),
                "osce_contribution": round(combined_osce_rnp_score * self.osce_weight, 2),
                "ml_contribution": round(ml_score * self.ml_weight, 2),
            },
            "individual_scores": {
                "sunat_estado": round(sunat_data["estado_score"], 2),
                "sunat_condicion": round(sunat_data["condicion_score"], 2),
                "sunat_deuda": round(sunat_data["debt_score"], 2),
                "antiguedad": round(antiguedad_score, 2),
                "antiguedad_years": antiguedad_years,
                "osce": round(osce_score, 2),
                "rnp_tce": round(rnp_score, 2),
                "osce_rnp_combined": round(combined_osce_rnp_score, 2),
                "ml": round(ml_score, 2),
            },
            "osce_analysis": osce_data,
            "rnp_tce_analysis": rnp_data,
            "reincidencia": {
                "nivel": reincidencia_nivel,
                "cantidad_total": cantidad_total,
                "penalty": reincidencia_penalty
            } if reincidencia_nivel else None,
            "ml_analysis": {
                "anomaly_score": round(100 - ml_score, 2),
                "risk_factors": ml_factors,
                "confidence": round(ml_confidence, 2)
            }
        }

    def get_risk_description(self, risk_level: str) -> str:
        """Retorna descripción del nivel de riesgo para compliance."""
        descriptions = {
            "low": "✅ Riesgo bajo. Empresa con buen perfil de cumplimiento. Apta para contratación.",
            "medium": "⚠️ Riesgo moderado. Se recomienda revisión adicional antes de contratar.",
            "high": "🚫 Riesgo alto. Detectadas irregularidades significativas. Contratación desaconsejada.",
            "critical": "⛔ RIESGO CRÍTICO. Historial de sanciones graves. NO RECOMENDADO para contratación pública."
        }
        return descriptions.get(risk_level, "Nivel de riesgo desconocido")

# Instancia global
scoring_engine = ScoringEngine()
