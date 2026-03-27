"""
Servicio de comparación de RUCs
Permite comparar múltiples RUCs simultáneamente
"""
import asyncio
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.services.data_collection import collect_all_data, calculate_risk_score


async def compare_rucs(rucs: List[str], db: Session = None) -> Dict[str, Any]:
    """
    Compara múltiples RUCs y retorna resultados ordenados por score.
    
    Args:
        rucs: Lista de RUCs a comparar (2-10 RUCs)
        db: Sesión de base de datos (opcional)
        
    Returns:
        Dict con resultados ordenados y metadatos de comparación
    """
    results = []
    errors = []
    
    for ruc in rucs:
        try:
            # Colectar datos del RUC
            data = await collect_all_data(ruc)
            
            # Calcular score
            score_result = calculate_risk_score(data)
            
            result = {
                "ruc": ruc,
                "razon_social": data.get("razon_social", "No disponible"),
                "score": score_result["score"],
                "risk_level": score_result["risk_level"],
                "estado_sunat": data.get("sunat", {}).get("estado", "DESCONOCIDO"),
                "condicion": data.get("sunat", {}).get("condicion", "DESCONOCIDO"),
                "sanciones_osce": data.get("osce", {}).get("sanciones_vigentes", 0),
                "sanciones_tce": data.get("rnp", {}).get("sanciones_vigentes", 0),
                "deuda_sunat": data.get("sunat", {}).get("deuda", 0),
                "fines_detalle": score_result.get("fines_summary", [])
            }
            results.append(result)
            
        except Exception as e:
            import traceback
            print(f"[Compare] Error con RUC {ruc}: {e}")
            print(traceback.format_exc())
            errors.append({
                "ruc": ruc,
                "error": str(e)
            })
    
    # Ordenar por score descendente
    results_sorted = sorted(results, key=lambda x: x["score"], reverse=True)
    
    # Calcular estadísticas de comparación
    if results:
        scores = [r["score"] for r in results]
        avg_score = sum(scores) / len(scores)
        best_ruc = results_sorted[0] if results_sorted else None
        worst_ruc = results_sorted[-1] if results_sorted else None
        
        risk_distribution = {
            "low": len([r for r in results if r["risk_level"] == "low"]),
            "medium": len([r for r in results if r["risk_level"] == "medium"]),
            "high": len([r for r in results if r["risk_level"] == "high"]),
            "critical": len([r for r in results if r["risk_level"] == "critical"])
        }
    else:
        avg_score = 0
        best_ruc = None
        worst_ruc = None
        risk_distribution = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    
    return {
        "total_compared": len(rucs),
        "successful": len(results),
        "failed": len(errors),
        "results": results_sorted,
        "errors": errors,
        "comparison_summary": {
            "average_score": round(avg_score, 2),
            "best_ruc": best_ruc,
            "worst_ruc": worst_ruc,
            "risk_distribution": risk_distribution,
            "score_range": {
                "min": min(scores) if scores else 0,
                "max": max(scores) if scores else 0
            }
        }
    }
