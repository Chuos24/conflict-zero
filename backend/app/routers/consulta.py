import requests
import os
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional

from app.core.database import get_db
from app.core.config import get_settings
from app.core.security import get_current_active_user
from app.services.scoring import scoring_engine
from app.services.scraping import scraping_service
from app.services.rnp_datos import rnp_service
from app.models import User

settings = get_settings()
router = APIRouter(tags=["Consulta Completa"])

# Función fallback - obtiene datos de SUNAT desde DB local
def get_sunat_fallback(ruc: str, db) -> Dict[str, Any]:
    """Obtiene datos de SUNAT desde la base de datos local como fallback."""
    try:
        # Buscar en tabla de sanciones OSCE
        query = text("""
            SELECT DISTINCT nombre, ruc 
            FROM osce_sanciones_detalle 
            WHERE ruc = :ruc 
            LIMIT 1
        """)
        result = db.execute(query, {"ruc": ruc}).fetchone()
        
        if result and result[0]:
            return {
                "ruc": ruc,
                "razon_social": result[0],
                "nombre": result[0],
                "estado": "ACTIVO",
                "condicion": "HABIDO",
                "direccion": "",
                "departamento": "",
                "provincia": "",
                "distrito": "",
                "ubigeo": "",
                "fuente": "osce_db_fallback",
                "success": True
            }
        
        # Si no está en OSCE, buscar en tabla osce_risk_data
        query2 = text("""
            SELECT ruc, nombre_razon_social
            FROM osce_risk_data
            WHERE ruc = :ruc
            LIMIT 1
        """)
        result2 = db.execute(query2, {"ruc": ruc}).fetchone()
        
        if result2 and result2[1]:
            return {
                "ruc": ruc,
                "razon_social": result2[1],
                "nombre": result2[1],
                "estado": "ACTIVO",
                "condicion": "HABIDO",
                "direccion": "",
                "departamento": "",
                "provincia": "",
                "distrito": "",
                "ubigeo": "",
                "fuente": "osce_risk_fallback",
                "success": True
            }
    except Exception as e:
        print(f"[FALLBACK] Error: {e}")
    
    # Fallback final: datos mínimos
    return {
        "ruc": ruc,
        "razon_social": "",
        "nombre": "",
        "estado": "ACTIVO",
        "condicion": "HABIDO",
        "direccion": "",
        "departamento": "",
        "provincia": "",
        "distrito": "",
        "ubigeo": "",
        "fuente": "minimal_fallback",
        "success": True
    }

# Función Perú API - alternativa confiable
def call_peru_api(ruc: str, db) -> Dict[str, Any]:
    """Llama a Perú API (peruapi.com) como fuente primaria."""
    token = os.environ.get("PERUAPI_TOKEN") or os.environ.get("PERU_API_KEY")
    
    if not token:
        print(f"[PERUAPI] No token configured, using fallback")
        return get_sunat_fallback(ruc, db)
    
    try:
        url = f"https://peruapi.com/api/ruc/{ruc}?api_token={token}"
        headers = {
            "User-Agent": "ConflictZero-API/1.0",
            "Accept": "application/json"
        }
        
        print(f"[PERUAPI] Calling for RUC: {ruc}")
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()
        
        print(f"[PERUAPI] Response code: {data.get('code')}")
        
        if data.get("code") == "200":
            return {
                "ruc": ruc,
                "razon_social": data.get("razon_social", "").strip(),
                "nombre": data.get("razon_social", "").strip(),
                "estado": data.get("estado", "ACTIVO").upper(),
                "condicion": data.get("condicion", "HABIDO").upper(),
                "direccion": data.get("direccion", "").strip(),
                "departamento": data.get("departamento", ""),
                "provincia": data.get("provincia", ""),
                "distrito": data.get("distrito", ""),
                "ubigeo": data.get("ubigeo", ""),
                "fuente": "peruapi_sunat",
                "success": True
            }
        else:
            print(f"[PERUAPI] Error: {data.get('mensaje')}")
            return get_sunat_fallback(ruc, db)
            
    except Exception as e:
        print(f"[PERUAPI] Exception: {e}")
        return get_sunat_fallback(ruc, db)

# Función APIPeru.dev - alternativa confiable (POST)
def call_apiperu_dev(ruc: str, db) -> Dict[str, Any]:
    """Llama a APIPeru.dev como fuente primaria."""
    token = os.environ.get("APIPERU_TOKEN") or os.environ.get("APIPERU_DEV_TOKEN")
    
    if not token:
        print(f"[APIPERU] No token configured, skipping")
        return {"fuente": "not_configured", "ruc": ruc}
    
    try:
        url = "https://apiperu.dev/api/ruc"
        headers = {
            "User-Agent": "ConflictZero-API/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        payload = {"ruc": ruc}
        
        print(f"[APIPERU] Calling for RUC: {ruc}")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        print(f"[APIPERU] Response success: {data.get('success')}")
        
        if data.get("success") and data.get("data"):
            d = data["data"]
            return {
                "ruc": ruc,
                "razon_social": d.get("nombre_o_razon_social", "").strip(),
                "nombre": d.get("nombre_o_razon_social", "").strip(),
                "estado": d.get("estado", "ACTIVO").upper(),
                "condicion": d.get("condicion", "HABIDO").upper(),
                "direccion": d.get("direccion", "").strip(),
                "departamento": d.get("departamento", ""),
                "provincia": d.get("provincia", ""),
                "distrito": d.get("distrito", ""),
                "ubigeo": d.get("ubigeo_sunat", ""),
                "fuente": "apiperu_dev",
                "success": True
            }
        else:
            print(f"[APIPERU] Error: {data}")
            return {"fuente": "apiperu_failed", "ruc": ruc}
            
    except Exception as e:
        print(f"[APIPERU] Exception: {e}")
        return {"fuente": "apiperu_error", "ruc": ruc}

# Función directa - llama a BuscarUC API
def call_buscaruc_api(ruc: str, db) -> Dict[str, Any]:
    """Llama directamente a BuscarUC API."""
    # Token hardcodeado de BuscarUC
    BUSCARUC_TOKEN = "eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE"
    token = os.environ.get("BUSCARUC_TOKEN") or os.environ.get("PERU_API_KEY") or os.environ.get("PERUAPI_TOKEN") or BUSCARUC_TOKEN
    
    if not token:
        print(f"[BUSCARUC] ERROR: No token found!")
        return {"error": True, "message": "API no configurada", "ruc": ruc}
    
    try:
        url = "https://buscaruc.com/api/v1/ruc"
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Accept-Language": "es-PE,es;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Origin": "https://czperu.com",
            "Referer": "https://czperu.com/"
        }
        payload = {"token": token, "ruc": ruc}
        
        print(f"[BUSCARUC] Calling for RUC: {ruc}")
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        data = response.json()
        
        print(f"[BUSCARUC] Response: {data.get('error', 'OK')}")
        
        # BuscarUC retorna datos en: data.result con campos en inglés
        if not data.get("error") and data.get("result"):
            result = data.get("result", {})
            return {
                "ruc": ruc,
                "razon_social": result.get("social_reason", "").strip(),
                "nombre": result.get("social_reason", "").strip(),
                "estado": result.get("taxpayer_state", "ACTIVO").upper(),
                "condicion": result.get("domicile_condition", "HABIDO").upper(),
                "direccion": result.get("address", "").strip(),
                "departamento": result.get("department", ""),
                "provincia": result.get("province", ""),
                "distrito": result.get("district", ""),
                "ubigeo": result.get("ubigeo", ""),
                "fuente": "buscaruc_sunat",
                "success": True
            }
        else:
            # BuscarUC falló, usar fallback a base de datos local
            print(f"[BUSCARUC] Error o sin datos, usando fallback para RUC: {ruc}")
            return get_sunat_fallback(ruc, db)
            
    except Exception as e:
        print(f"[BUSCARUC] Exception: {e}")
        return {"error": True, "message": str(e), "ruc": ruc}


@router.get(
    "/consulta-completa/{ruc}",
    summary="Consulta Completa de RUC",
    description="Consulta SUNAT y calcula score predictivo basado en datos disponibles."
)
async def consulta_completa(
    ruc: str,
    db: Session = Depends(get_db)
):
    """
    Endpoint principal de consulta RUC.
    Consulta datos de SUNAT vía BuscarUC y calcula score predictivo.
    """
    # Validar RUC
    if len(ruc) != 11 or not ruc.isdigit():
        return {
            "error": True,
            "message": "RUC debe tener 11 dígitos numéricos",
            "ruc": ruc
        }
    
    # Llamada a APIPeru.dev (primera opción)
    sunat_data = call_apiperu_dev(ruc, db)
    
    # Si APIPeru.dev falla o no está configurado, intentar Perú API
    if not sunat_data.get("success"):
        print(f"[CONSULTA] APIPeru.dev falló, intentando Perú API...")
        sunat_data = call_peru_api(ruc, db)
    
    # Si Perú API también falla, intentar BuscarUC
    if sunat_data.get("fuente") == "minimal_fallback":
        print(f"[CONSULTA] Perú API falló, intentando BuscarUC...")
        buscaruc_data = call_buscaruc_api(ruc, db)
        if buscaruc_data.get("fuente") != "minimal_fallback":
            sunat_data = buscaruc_data
    
    # Si BuscarUC falla O devuelve datos incompletos (sin razón social), usar fallback
    buscaruc_failed = sunat_data.get("error") or not sunat_data.get("razon_social")
    
    if buscaruc_failed:
        from app.services.osce_datos_abiertos import osce_datos_abiertos
        osce_db_data = osce_datos_abiertos.get_sanciones_from_db(ruc)
        
        razon_social_fallback = None
        if osce_db_data and osce_db_data.get("nombre"):
            razon_social_fallback = osce_db_data.get("nombre")
        elif sunat_data.get("razon_social"):
            # Usar lo que vino de BuscarUC aunque sea incompleto
            razon_social_fallback = sunat_data.get("razon_social")
        else:
            razon_social_fallback = f"RUC {ruc}"
        
        if osce_db_data:
            # Usar datos de OSCE como fallback
            sunat_data = {
                "ruc": ruc,
                "razon_social": razon_social_fallback,
                "nombre": osce_db_data.get("nombre", ""),
                "estado": sunat_data.get("estado", "ACTIVO"),
                "condicion": sunat_data.get("condicion", "HABIDO"),
                "direccion": sunat_data.get("direccion", ""),
                "departamento": sunat_data.get("departamento", ""),
                "provincia": sunat_data.get("provincia", ""),
                "distrito": sunat_data.get("distrito", ""),
                "ubigeo": sunat_data.get("ubigeo", ""),
                "success": True,
                "fuente": "osce_db_fallback"
            }
        else:
            # Último fallback: usar lo que tengamos de BuscarUC o solo el RUC
            sunat_data = {
                "ruc": ruc,
                "razon_social": razon_social_fallback,
                "nombre": sunat_data.get("nombre", ""),
                "estado": sunat_data.get("estado", "ACTIVO"),
                "condicion": sunat_data.get("condicion", "HABIDO"),
                "direccion": sunat_data.get("direccion", ""),
                "departamento": sunat_data.get("departamento", ""),
                "provincia": sunat_data.get("provincia", ""),
                "distrito": sunat_data.get("distrito", ""),
                "ubigeo": sunat_data.get("ubigeo", ""),
                "success": True,
                "fuente": "ruc_only"
            }
    
    # Consultar sanciones OSCE (datos reales de CONOSCE)
    osce_sanciones = scraping_service.get_osce_sanctions(ruc)
    
    # Consultar sanciones RNP/TCE (nueva fuente)
    rnp_sanciones = rnp_service.get_sanciones_detalle(ruc)
    
    # Calcular score usando el scoring engine con datos reales
    score_result = scoring_engine.calculate_total_score(
        ruc=ruc,
        razon_social=sunat_data.get("razon_social", ""),
        estado=sunat_data.get("estado", "ACTIVO"),
        condicion=sunat_data.get("condicion", "HABIDO"),
        deuda=0,  # No disponible en BuscarUC
        osce_sanctions=osce_sanciones,
        tce_sanctions=rnp_sanciones
    )
    
    # Combinar sanciones para el conteo total
    total_sanciones = osce_sanciones + rnp_sanciones
    
    # Construir respuesta completa con sanciones reales
    return {
        "ruc": ruc,
        "razon_social": sunat_data.get("razon_social", "No disponible"),
        "nombre_comercial": sunat_data.get("nombre", sunat_data.get("razon_social", "")),
        "estado": sunat_data.get("estado", "ACTIVO"),
        "condicion": sunat_data.get("condicion", "HABIDO"),
        "estado_sunat": sunat_data.get("estado", "ACTIVO"),
        "direccion": sunat_data.get("direccion", ""),
        "departamento": sunat_data.get("departamento", ""),
        "provincia": sunat_data.get("provincia", ""),
        "distrito": sunat_data.get("distrito", ""),
        "ubigeo": sunat_data.get("ubigeo", ""),
        "score": score_result["total_score"],
        "risk_level": score_result["risk_level"],
        "risk_emoji": score_result["risk_emoji"],
        "risk_description": scoring_engine.get_risk_description(score_result["risk_level"]),
        "sunat": {
            "ruc": ruc,
            "razon_social": sunat_data.get("razon_social", ""),
            "estado": sunat_data.get("estado", "ACTIVO"),
            "condicion": sunat_data.get("condicion", "HABIDO"),
            "direccion": sunat_data.get("direccion", "")
        },
        "sanciones": total_sanciones,
        "sanciones_osce": osce_sanciones,
        "sanciones_rnp_tce": rnp_sanciones,
        "total_registros": len(total_sanciones),
        "fuentes": {
            "sunat": True,
            "osce": len(osce_sanciones),
            "rnp_tce": len(rnp_sanciones)
        },
        "score_breakdown": score_result["breakdown"],
        "score_details": score_result["individual_scores"],
        "fuente_datos": sunat_data.get("fuente", "buscaruc"),
        "score_detalle": score_result,
        "ml_analysis": score_result["ml_analysis"]
    }


@router.get(
    "/sunat/ruc/{ruc}",
    summary="Consulta SUNAT Directa",
    description="Obtiene datos básicos de SUNAT para un RUC."
)
async def consulta_sunat(ruc: str, db: Session = Depends(get_db)):
    """Endpoint simple de consulta SUNAT."""
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": "RUC inválido"}
    
    # Intentar APIPeru.dev primero, luego Perú API, luego BuscarUC, luego fallback
    data = call_apiperu_dev(ruc, db)
    if not data.get("success"):
        data = call_peru_api(ruc, db)
    if data.get("fuente") == "minimal_fallback":
        data = call_buscaruc_api(ruc, db)
    
    return data


@router.get(
    "/score/ruc/{ruc}",
    summary="Score Predictivo de RUC",
    description="Obtiene solo el score y análisis de riesgo para un RUC."
)
async def consulta_score(ruc: str):
    """Endpoint para obtener solo el score de un RUC."""
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": True, "message": "RUC inválido"}
    
    sunat_data = call_buscaruc_api(ruc, db)
    
    if sunat_data.get("error"):
        return sunat_data
    
    score_result = scoring_engine.calculate_total_score(
        ruc=ruc,
        razon_social=sunat_data.get("razon_social", ""),
        estado=sunat_data.get("estado", "ACTIVO"),
        condicion=sunat_data.get("condicion", "HABIDO"),
        deuda=0,
        osce_sanctions=[],
        tce_sanctions=[]
    )
    
    return {
        "ruc": ruc,
        "razon_social": sunat_data.get("razon_social", ""),
        "score": score_result["total_score"],
        "risk_level": score_result["risk_level"],
        "risk_emoji": score_result["risk_emoji"],
        "risk_description": scoring_engine.get_risk_description(score_result["risk_level"]),
        "score_breakdown": score_result["breakdown"],
        "ml_analysis": score_result["ml_analysis"]
    }


# ============================================================================
# ADMIN ENDPOINTS - Gestión de Sanciones
# ============================================================================

@router.post(
    "/admin/sanciones/update",
    summary="[ADMIN] Actualizar Sanción",
    description="Actualiza el estado y fechas de una sanción OSCE. Requiere autenticación de administrador.",
    response_model=Dict[str, Any]
)
async def admin_update_sancion(
    ruc: str,
    numero_resolucion: str,
    nuevo_estado: str,
    fecha_fin: Optional[str] = None,
    nota: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Endpoint administrativo para corregir sanciones.
    
    - **ruc**: RUC de la empresa sancionada
    - **numero_resolucion**: Número de resolución (ej: 4162-2023-TCE-S4)
    - **nuevo_estado**: VIGENTE o VENCIDA
    - **fecha_fin**: Fecha de fin en formato YYYY-MM-DD (opcional)
    - **nota**: Nota adicional sobre el cambio (opcional)
    
    Ejemplo de uso:
    ```json
    {
        "ruc": "20529400790",
        "numero_resolucion": "4162-2023-TCE-S4",
        "nuevo_estado": "VENCIDA",
        "fecha_fin": "2025-12-31",
        "nota": "Reducido a 26 meses por Resolución 6981-2025-TCP-S4"
    }
    ```
    """
    try:
        # Verificar que el usuario es admin
        if not getattr(current_user, 'is_admin', False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Se requieren privilegios de administrador"
            )
        
        # Buscar la sanción
        result = db.execute(
            text("""
                SELECT id, ruc, numero_resolucion, fecha_inicio, fecha_fin, estado, motivo 
                FROM osce_sanciones_detalle 
                WHERE ruc = :ruc AND numero_resolucion LIKE :resolucion
            """),
            {
                'ruc': ruc,
                'resolucion': f'%{numero_resolucion}%'
            }
        ).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sanción no encontrada: {numero_resolucion} para RUC {ruc}"
            )
        
        # Construir la nota final
        nota_final = result.motivo or ""
        if nota:
            nota_final += f" | [Admin Update] {nota}"
        
        # Actualizar la sanción
        update_query = """
            UPDATE osce_sanciones_detalle 
            SET estado = :estado,
                motivo = :motivo
        """
        params = {
            'estado': nuevo_estado,
            'motivo': nota_final,
            'id': result.id
        }
        
        if fecha_fin:
            update_query += ", fecha_fin = :fecha_fin"
            params['fecha_fin'] = fecha_fin
        
        update_query += " WHERE id = :id"
        
        db.execute(text(update_query), params)
        db.commit()
        
        # Invalidar caché si existe
        try:
            from app.core.cache import cache
            cache.delete(f"osce_sanciones:{ruc}")
            cache.delete(f"consulta_completa:{ruc}")
        except:
            pass  # Cache no disponible
        
        return {
            "success": True,
            "message": "Sanción actualizada correctamente",
            "data": {
                "ruc": ruc,
                "numero_resolucion": numero_resolucion,
                "estado_anterior": result.estado,
                "estado_nuevo": nuevo_estado,
                "fecha_fin_anterior": str(result.fecha_fin) if result.fecha_fin else None,
                "fecha_fin_nueva": fecha_fin,
                "actualizado_por": current_user.email,
                "nota": nota
            },
            "next_steps": [
                "El score se recalculará automáticamente en la próxima consulta",
                "Cache invalidada para este RUC"
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando sanción: {str(e)}"
        )


@router.get(
    "/admin/sanciones/list/{ruc}",
    summary="[ADMIN] Listar Sanciones",
    description="Lista todas las sanciones de un RUC para revisión."
)
async def admin_list_sanciones(
    ruc: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Lista sanciones de un RUC (admin only)."""
    # Verificar que el usuario es admin
    if not getattr(current_user, 'is_admin', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren privilegios de administrador"
        )
    
    result = db.execute(
        text("""
            SELECT id, ruc, nombre, numero_resolucion, 
                   fecha_inicio, fecha_fin, estado, tipo_sancion, motivo
            FROM osce_sanciones_detalle 
            WHERE ruc = :ruc
            ORDER BY fecha_inicio DESC
        """),
        {'ruc': ruc}
    ).fetchall()
    
    return {
        "ruc": ruc,
        "total_sanciones": len(result),
        "sanciones": [
            {
                "id": row.id,
                "numero_resolucion": row.numero_resolucion,
                "nombre": row.nombre,
                "fecha_inicio": str(row.fecha_inicio) if row.fecha_inicio else None,
                "fecha_fin": str(row.fecha_fin) if row.fecha_fin else None,
                "estado": row.estado,
                "tipo_sancion": row.tipo_sancion,
                "motivo": row.motivo
            }
            for row in result
        ]
    }
# Deploy force Fri Mar 27 12:10:25 AM CST 2026
