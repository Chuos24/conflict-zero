import requests
import os
import json
from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional, List

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
        # PRIMERO: Buscar en ruc_cache (tabla de respaldo prioritaria)
        query_cache = text("""
            SELECT ruc, razon_social, nombre_comercial, estado, condicion,
                   direccion, departamento, provincia, distrito, ubigeo
            FROM ruc_cache 
            WHERE ruc = :ruc 
            LIMIT 1
        """)
        cache_result = db.execute(query_cache, {"ruc": ruc}).fetchone()
        
        if cache_result:
            return {
                "ruc": ruc,
                "razon_social": cache_result[1],
                "nombre": cache_result[2] or cache_result[1],
                "estado": cache_result[3] or "ACTIVO",
                "condicion": cache_result[4] or "HABIDO",
                "direccion": cache_result[5] or "",
                "departamento": cache_result[6] or "",
                "provincia": cache_result[7] or "",
                "distrito": cache_result[8] or "",
                "ubigeo": cache_result[9] or "",
                "fuente": "ruc_cache",
                "success": True
            }
        
        # SEGUNDO: Buscar en tabla de sanciones OSCE
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
        
        # TERCERO: Buscar en tabla osce_risk_data
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

# Función Factiliza.com - nueva fuente primaria
def call_factiliza_api(ruc: str, db) -> Dict[str, Any]:
    """Llama a Factiliza.com como fuente primaria."""
    token = os.environ.get("FACTILIZA_TOKEN")
    
    if not token:
        print(f"[FACTILIZA] No token configured, skipping")
        return {"fuente": "not_configured", "ruc": ruc}
    
    try:
        url = f"https://api.factiliza.com/v1/ruc/info/{ruc}"
        headers = {
            "User-Agent": "ConflictZero-API/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }

        print(f"[FACTILIZA] Calling for RUC: {ruc}")
        response = requests.get(url, headers=headers, timeout=15)
        data = response.json()

        print(f"[FACTILIZA] Response status: {data.get('status')} success: {data.get('success')}")

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
                "fuente": "factiliza_api",
                "success": True
            }
        else:
            print(f"[FACTILIZA] Error: {data.get('message', data.get('error', 'Unknown error'))}")
            return {"fuente": "factiliza_failed", "ruc": ruc}
            
    except Exception as e:
        print(f"[FACTILIZA] Exception: {e}")
        return {"fuente": "factiliza_error", "ruc": ruc}

# Función apis.net.pe - fuente adicional gratuita
def call_apis_net_pe(ruc: str, db) -> Dict[str, Any]:
    """Llama a apis.net.pe como fuente alternativa gratuita."""
    token = os.environ.get("APIS_NET_PE_TOKEN")
    
    # Token por defecto (gratuito con límite)
    if not token:
        token = "apis-token-1.aTSI1T-ce2Rg8L7NZ42T0-ljQ8jV-EG"
    
    try:
        url = f"https://api.apis.net.pe/v2/sunat/ruc/full?numero={ruc}"
        headers = {
            "User-Agent": "ConflictZero-API/1.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        print(f"[APIS_NET_PE] Calling for RUC: {ruc}")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            d = response.json()
            return {
                "ruc": ruc,
                "razon_social": d.get("razonSocial", "").strip() or d.get("nombre", "").strip(),
                "nombre": d.get("razonSocial", "").strip() or d.get("nombre", "").strip(),
                "estado": d.get("estado", "ACTIVO").upper(),
                "condicion": d.get("condicion", "HABIDO").upper(),
                "direccion": d.get("direccion", "").strip(),
                "departamento": d.get("departamento", ""),
                "provincia": d.get("provincia", ""),
                "distrito": d.get("distrito", ""),
                "ubigeo": d.get("ubigeo", ""),
                "fuente": "apis_net_pe",
                "success": True
            }
        else:
            print(f"[APIS_NET_PE] Error: HTTP {response.status_code}")
            return {"fuente": "apis_net_pe_failed", "ruc": ruc}
            
    except Exception as e:
        print(f"[APIS_NET_PE] Exception: {e}")
        return {"fuente": "apis_net_pe_error", "ruc": ruc}


# Función scraping SUNAT - último recurso
def call_sunat_scraping(ruc: str, db) -> Dict[str, Any]:
    """Scraping de SUNAT como último recurso."""
    try:
        print(f"[SUNAT_SCRAPING] Intentando scraping para RUC: {ruc}")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-PE,es;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        # Paso 1: Obtener cookie de sesión
        init_url = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
        r1 = session.get(init_url, timeout=30)
        
        if r1.status_code != 200:
            print(f"[SUNAT_SCRAPING] Error inicial: {r1.status_code}")
            return {"fuente": "sunat_scraping_failed", "ruc": ruc}
        
        # Paso 2: Realizar consulta
        consulta_url = "https://e-consultaruc.sunat.gob.pe/cl-ti-itmrconsruc/jcrS00Alias"
        data = {"accion": "consPorRuc", "razSoc": "", "nroRuc": ruc, "nrodoc": "", "contexto": "ti-it", "search1": ruc, "codigo": "", "tipdoc": "1"}
        
        r2 = session.post(consulta_url, data=data, timeout=30)
        
        if r2.status_code == 200 and "razonSocial" in r2.text.lower():
            # Parsear HTML para extraer datos
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(r2.text, 'html.parser')
            
            # Buscar razón social
            razon_social = ""
            estado = "ACTIVO"
            condicion = "HABIDO"
            
            # Intentar extraer de diferentes formatos
            for tag in soup.find_all(['h4', 'h3', 'h2', 'span', 'div']):
                text = tag.get_text().strip()
                if len(text) > 10 and ruc in text:
                    razon_social = text.replace(ruc, "").strip(" -")
                    break
            
            if razon_social:
                return {
                    "ruc": ruc,
                    "razon_social": razon_social,
                    "nombre": razon_social,
                    "estado": estado,
                    "condicion": condicion,
                    "direccion": "",
                    "departamento": "",
                    "provincia": "",
                    "distrito": "",
                    "ubigeo": "",
                    "fuente": "sunat_scraping",
                    "success": True
                }
        
        print(f"[SUNAT_SCRAPING] No se pudo extraer datos del HTML")
        return {"fuente": "sunat_scraping_failed", "ruc": ruc}
        
    except Exception as e:
        print(f"[SUNAT_SCRAPING] Exception: {e}")
        return {"fuente": "sunat_scraping_error", "ruc": ruc}

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
    
    # Cascade: Factiliza → apis.net.pe → APIPeru.dev → Perú API → BuscarUC → DB local
    # Cada fuente solo se salta si la anterior devolvió un nombre real.
    def _got_name(d: dict) -> bool:
        return bool(d.get("success") and d.get("razon_social", "").strip())

    sunat_data = call_factiliza_api(ruc, db)

    if not _got_name(sunat_data):
        print(f"[CONSULTA] Factiliza sin nombre ({sunat_data.get('fuente')}), intentando apis.net.pe...")
        sunat_data = call_apis_net_pe(ruc, db)

    if not _got_name(sunat_data):
        print(f"[CONSULTA] apis.net.pe sin nombre ({sunat_data.get('fuente')}), intentando APIPeru.dev...")
        sunat_data = call_apiperu_dev(ruc, db)

    if not _got_name(sunat_data):
        print(f"[CONSULTA] APIPeru.dev sin nombre ({sunat_data.get('fuente')}), intentando Perú API...")
        sunat_data = call_peru_api(ruc, db)

    if not _got_name(sunat_data):
        print(f"[CONSULTA] Perú API sin nombre ({sunat_data.get('fuente')}), intentando BuscarUC...")
        sunat_data = call_buscaruc_api(ruc, db)

    if not _got_name(sunat_data):
        print(f"[CONSULTA] BuscarUC sin nombre ({sunat_data.get('fuente')}), intentando scraping SUNAT...")
        sunat_data = call_sunat_scraping(ruc, db)

    if not _got_name(sunat_data):
        print(f"[CONSULTA] Scraping SUNAT sin nombre ({sunat_data.get('fuente')}), intentando DB local...")
        sunat_data = get_sunat_fallback(ruc, db)

    # ¿Todavía sin nombre real tras todas las fuentes?
    buscaruc_failed = not _got_name(sunat_data)

    # Último recurso: DB local (osce_sanciones_detalle + osce_risk_data)
    if buscaruc_failed and not sunat_data.get("razon_social"):
        print(f"[CONSULTA] APIs externas fallaron, intentando DB local...")
        db_fallback = get_sunat_fallback(ruc, db)
        if db_fallback.get("razon_social"):
            sunat_data = db_fallback
            buscaruc_failed = False

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
    
    def _got_name(d: dict) -> bool:
        return bool(d.get("success") and d.get("razon_social", "").strip())

    data = call_factiliza_api(ruc, db)
    if not _got_name(data):
        data = call_apiperu_dev(ruc, db)
    if not _got_name(data):
        data = call_peru_api(ruc, db)
    if not _got_name(data):
        data = call_buscaruc_api(ruc, db)
    if not _got_name(data):
        data = get_sunat_fallback(ruc, db)

    return data


@router.get(
    "/score/ruc/{ruc}",
    summary="Score Predictivo de RUC",
    description="Obtiene solo el score y análisis de riesgo para un RUC."
)
async def consulta_score(ruc: str, db: Session = Depends(get_db)):
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


# ============================================================================
# LEGALBOT UNIVERSAL V3.0 - Scoring Multidimensional
# ============================================================================

from datetime import datetime, timedelta
from typing import List, Dict, Any

# Diccionario de gravedad por keywords
GRAVEDAD_KEYWORDS = {
    # 100 - Grave (Corrupción, fraude)
    100: ['colusión', 'cohecho', 'peculado', 'fraude', 'simulación', 'alteración', 'falsedad', 
          'inhabilitación definitiva', 'definitiva', 'corrupción', 'conspiración'],
    # 70 - Media-Alta (Impedimentos)
    70: ['impedimento', 'inhabilitación temporal', 'temporal', 'responsabilidad patrimonial',
         'incumplimiento grave', 'inexacta', 'falsos', 'adulterados'],
    # 60 - Media (Sanciones)
    60: ['sanción', 'multa grave', 'obstrucción', 'infracción', 'penalidad'],
    # 20 - Leve (Multas menores)
    20: ['multa tributaria', 'omisión', 'retraso', 'formalidad', 'documentación', 'tardanza'],
    # 10 - Mínima (Advertencias)
    10: ['observación', 'advertencia', 'llamada de atención', 'amonestación']
}

# Multiplicadores por entidad
ENTIDAD_MULTIPLICADORES = {
    'OSCE': 1.5,      # Crítico para constructoras
    'TCE': 1.2,       # Grave pero recuperable
    'SUNAT': 0.8,     # Menor impacto si pagada
    'INDECOPI': 1.0,  # Estándar
    'DEFAULT': 1.0
}

def detectar_gravedad(descripcion: str) -> int:
    """Detecta nivel de gravedad basado en keywords."""
    if not descripcion:
        return 60  # Default media
    
    desc_lower = descripcion.lower()
    
    for gravedad, keywords in GRAVEDAD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in desc_lower:
                return gravedad
    
    return 60  # Default media si no encuentra

def obtener_multiplicador_entidad(entidad: str) -> float:
    """Obtiene multiplicador según entidad sancionadora."""
    if not entidad:
        return ENTIDAD_MULTIPLICADORES['DEFAULT']
    
    entidad_upper = entidad.upper()
    
    for key, valor in ENTIDAD_MULTIPLICADORES.items():
        if key in entidad_upper:
            return valor
    
    return ENTIDAD_MULTIPLICADORES['DEFAULT']

def calcular_factor_tiempo(dias_transcurridos: int) -> float:
    """Calcula factor de decaimiento temporal."""
    if dias_transcurridos < 365:
        return 1.0  # Impacto total
    elif dias_transcurridos < 1095:  # 3 años
        return 0.7  # Moderado - Zona crítica
    elif dias_transcurridos < 1825:  # 5 años
        return 0.4  # Bajo - Recuperación
    else:
        return 0.1  # Mínimo - Casi limpio

def calcular_impacto_sancion(sancion: Dict[str, Any]) -> Dict[str, Any]:
    """Calcula el impacto de una sanción individual."""
    # Obtener descripción
    descripcion = sancion.get('description', '') or sancion.get('motivo', '') or sancion.get('tipo_sancion', '') or ''
    
    # Detectar gravedad
    gravedad = detectar_gravedad(descripcion)
    
    # Detectar entidad - extraer de múltiples fuentes posibles
    entidad = 'OSCE'  # default
    resolucion = sancion.get('sanction_id') or sancion.get('numero_resolucion') or ''
    
    # Intentar extraer entidad de la resolución (ej: 4162-2023-TCE-S4)
    if resolucion:
        res_upper = str(resolucion).upper()
        if 'TCE' in res_upper:
            entidad = 'TCE'
        elif 'OSCE' in res_upper:
            entidad = 'OSCE'
        elif 'SUNAT' in res_upper:
            entidad = 'SUNAT'
        elif 'INDECOPI' in res_upper:
            entidad = 'INDECOPI'
    
    # Fallback a campos de entidad si no se detectó de resolución
    if entidad == 'OSCE':
        entidad_raw = sancion.get('entity') or sancion.get('entidad') or sancion.get('fuente') or sancion.get('sancionador') or ''
        if entidad_raw:
            entidad = str(entidad_raw).strip()
    
    entidad_mult = obtener_multiplicador_entidad(entidad)
    
    # Calcular tiempo - intentar múltiples formatos de fecha
    fecha_inicio_str = (sancion.get('fecha_inicio') or sancion.get('date') or 
                       sancion.get('fecha') or sancion.get('fecha_sancion') or 
                       sancion.get('fecha_inicio_sancion') or sancion.get('periodo'))
    
    dias_transcurridos = 0
    factor_tiempo = 1.0
    fecha_debug = None
    fecha_forzada = None
    
    # 🚨 FALLBACK TEMPORAL: Hardcode para Zamora Jara (Padre - Founder #1)
    ruc_sancion = sancion.get('ruc', '')
    if ruc_sancion == '20529400790' and resolucion and '4162-2023-TCE-S4' in str(resolucion):
        fecha_forzada = datetime(2023, 9, 28)  # Fecha conocida de la resolución
        dias_transcurridos = (datetime.now() - fecha_forzada).days
        factor_tiempo = calcular_factor_tiempo(dias_transcurridos)
        fecha_debug = "2023-09-28 (FORZADA - Founder #1)"
    elif fecha_inicio_str:
        fecha_debug = str(fecha_inicio_str)[:50]
        try:
            # Si es un objeto date/datetime, convertir directamente
            if hasattr(fecha_inicio_str, 'year'):
                fecha_inicio = fecha_inicio_str
                if not hasattr(fecha_inicio, 'hour'):  # date object, not datetime
                    fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
            else:
                fecha_str = str(fecha_inicio_str).strip()
                # Intentar parsear ISO format
                if 'T' in fecha_str:
                    fecha_inicio = datetime.fromisoformat(fecha_str.replace('Z', '+00:00').replace('+00:00', ''))
                # Intentar dd/mm/yyyy
                elif '/' in fecha_str:
                    fecha_inicio = datetime.strptime(fecha_str, '%d/%m/%Y')
                # Intentar yyyy-mm-dd
                elif '-' in fecha_str and len(fecha_str) == 10:
                    fecha_inicio = datetime.strptime(fecha_str, '%Y-%m-%d')
                else:
                    fecha_inicio = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
            
            dias_transcurridos = (datetime.now() - fecha_inicio).days
            factor_tiempo = calcular_factor_tiempo(dias_transcurridos)
        except Exception as e:
            print(f"[LegalBot V3] Error parsing fecha '{fecha_inicio_str}' (tipo: {type(fecha_inicio_str)}): {e}")
            pass
    else:
        # 🚨 HEURÍSTICA PARA CLIENTES DEL LUNES: Extraer año de la resolución
        # Patrones tipo: 4162-2023-TCE-S4, RES-2023-123, etc.
        if resolucion:
            import re
            año_match = re.search(r'[-/](20\d{2})[-/]', str(resolucion))
            if año_match:
                año = int(año_match.group(1))
                # Usar 1 de julio del año encontrado como fecha aproximada
                fecha_aprox = datetime(año, 7, 1)
                dias_transcurridos = (datetime.now() - fecha_aprox).days
                factor_tiempo = calcular_factor_tiempo(dias_transcurridos)
                fecha_debug = f"{año} (ESTIMADO de resolución)"
                print(f"[LegalBot V3] Fecha estimada de resolución '{resolucion}': {año}")
            else:
                print(f"[LegalBot V3] No fecha encontrada. Keys: {list(sancion.keys())}")
        else:
            print(f"[LegalBot V3] No fecha ni resolución encontrada.")
    
    # Calcular impacto
    impacto = gravedad * entidad_mult * factor_tiempo
    
    return {
        'resolucion': resolucion or 'N/A',
        'descripcion': descripcion[:100] + '...' if len(descripcion) > 100 else descripcion,
        'gravedad_base': gravedad,
        'entidad': entidad,
        'entidad_mult': entidad_mult,
        'dias_transcurridos': dias_transcurridos,
        'anios': round(dias_transcurridos / 365.25, 1),
        'factor_tiempo': factor_tiempo,
        'impacto': round(impacto, 1),
        'fecha_info': fecha_debug  # Muestra origen de la fecha
    }

def calculate_legalbot_v3(sanciones: List[Dict[str, Any]], ruc: str = '') -> Dict[str, Any]:
    """
    LEGALBOT UNIVERSAL V3.0 - Scoring Multidimensional
    
    Fórmula: impacto = gravedad × entidad_mult × factor_tiempo
    score = 100 - Σ(impacto de cada sanción)
    """
    if not sanciones:
        return {
            'score': 100,
            'tier': 'GOLD',
            'status': 'APTO',
            'detalles': [],
            'impacto_total': 0,
            'confianza': 1.0,
            'metodo': 'LEGALBOT_V3_MULTIDIMENSIONAL'
        }
    
    detalles = []
    impacto_total = 0
    tiene_definitiva = False
    
    for sancion in sanciones:
        # Agregar RUC a la sanción para el fallback
        sancion_con_ruc = dict(sancion)
        sancion_con_ruc['ruc'] = ruc
        detalle = calcular_impacto_sancion(sancion_con_ruc)
        detalles.append(detalle)
        impacto_total += detalle['impacto']
        
        # Detectar inhabilitación definitiva
        if detalle['gravedad_base'] == 100:
            tiene_definitiva = True
    
    # Calcular score final
    score = max(0, 100 - impacto_total)
    
    # Aplicar CAP si tiene definitiva
    if tiene_definitiva:
        score = 0
        tier = 'RECHAZADO'
        status = 'BLOQUEO_PERMANENTE'
    else:
        # Determinar tier según score
        if score >= 90:
            tier = 'GOLD'
            status = 'APTO'
        elif score >= 70:
            tier = 'SILVER'
            status = 'APTO'
        elif score >= 30:
            tier = 'BRONZE'
            status = 'APTO'
        else:
            tier = 'RECHAZADO'
            status = 'RECHAZADO'
    
    return {
        'score': round(score),
        'tier': tier,
        'status': status,
        'detalles': detalles,
        'impacto_total': round(impacto_total, 1),
        'sanciones_count': len(sanciones),
        'tiene_definitiva': tiene_definitiva,
        'confianza': 0.95 if len(sanciones) <= 3 else 0.85,
        'metodo': 'LEGALBOT_V3_MULTIDIMENSIONAL'
    }
    """
    LEGALBOT UNIVERSAL V2.0
    Algoritmo universal que aplica a CUALQUIER RUC según Ley 30225.
    
    Zonas temporales:
    - < 730 días (2 años): Sanción fresca - Score 0-20
    - 730-1095 días (2-3 años): ZONA CRÍTICA - Score 50, requiere verificación
    - > 1095 días (3+ años): Recuperación gradual - Score 75-95
    
    Returns:
        Dict con score, tier, fecha_desbloqueo, confianza, flags
    """
    hoy = datetime.now()
    score_osce = 100
    fecha_bloqueo = None
    requiere_verificacion = False
    es_definitiva = False
    dias_max_sancion = 0
    
    for sancion in sanciones:
        # Obtener fecha de inicio
        fecha_inicio_str = sancion.get('fecha_inicio') or sancion.get('date')
        if not fecha_inicio_str:
            continue
            
        try:
            if 'T' in str(fecha_inicio_str):
                fecha_inicio = datetime.fromisoformat(str(fecha_inicio_str).replace('Z', '+00:00').replace('+00:00', ''))
            else:
                fecha_inicio = datetime.strptime(str(fecha_inicio_str), '%Y-%m-%d')
        except:
            continue
        
        dias_transcurridos = (hoy - fecha_inicio).days
        dias_max_sancion = max(dias_max_sancion, dias_transcurridos)
        
        # Detectar tipo de sanción
        tipo = sancion.get('tipo', '').upper()
        tipo_sancion = sancion.get('tipo_sancion', '').upper() if sancion.get('tipo_sancion') else ''
        descripcion = (sancion.get('description', '') + sancion.get('motivo', '')).upper()
        
        # CASO 1: Inhabilitación Definitiva (Corrupción grave)
        if 'DEFINITIVA' in tipo or 'DEFINITIVA' in tipo_sancion or 'DEFINITIVA' in descripcion:
            es_definitiva = True
            return {
                'score': 0,
                'tier': 'RECHAZADO',
                'status': 'BLOQUEO_PERMANENTE',
                'motivo': 'Inhabilitación definitiva - Requiere rehabilitación judicial',
                'automatico': True,
                'confianza': 1.0,
                'zona_critica': False,
                'fecha_desbloqueo_gold': None,
                'dias_ley_aplicados': 1095,
                'metodo_calculo': 'LEY_30225_DEFINITIVA'
            }
        
        # Determinar tipo default si no está especificado
        if not tipo:
            tipo = 'TEMPORAL'
        
        # CASO 2: Sanción fresca (< 2 años) - Aún muy caliente
        if dias_transcurridos < 730:
            score_osce = min(score_osce, 20)
            fecha_bloqueo_candidate = fecha_inicio + timedelta(days=730)
            if fecha_bloqueo is None or fecha_bloqueo_candidate > fecha_bloqueo:
                fecha_bloqueo = fecha_bloqueo_candidate
        
        # CASO 3: ZONA CRÍTICA (2-3 años) - Heurística legal
        elif 730 <= dias_transcurridos < 1095:
            score_osce = min(score_osce, 50)
            fecha_bloqueo = fecha_inicio + timedelta(days=1095)  # Asumir máximo legal
            requiere_verificacion = True
        
        # CASO 4: Sanción madura (> 3 años) - Recuperación gradual
        elif dias_transcurridos >= 1095:
            años_expirado = (dias_transcurridos - 1095) / 365.25
            # Recuperación: 75 base + 5 por cada año adicional, máximo 95
            score_recuperacion = min(95, 75 + (años_expirado * 5))
            score_osce = min(score_osce, score_recuperacion)
    
    # Si no tiene sanciones, score perfecto
    if not sanciones:
        score_osce = 100
    
    # Determinar tier universal
    if score_osce >= 90:
        tier = 'GOLD'
    elif score_osce >= 70:
        tier = 'SILVER'
    elif score_osce >= 30:
        tier = 'BRONZE'
        if requiere_verificacion:
            tier = 'BRONZE_VERIFICACION'
    else:
        tier = 'RECHAZADO'
    
    # Calcular confianza
    confianza = 0.95 if not requiere_verificacion else 0.65
    
    return {
        'score': int(score_osce),
        'tier': tier,
        'status': 'VIGENTE' if score_osce > 0 else 'BLOQUEADO',
        'fecha_desbloqueo_gold': fecha_bloqueo.isoformat() if fecha_bloqueo else None,
        'confianza': round(confianza, 2),
        'automatico': not requiere_verificacion,
        'requiere_verificacion': requiere_verificacion,
        'zona_critica': requiere_verificacion,
        'dias_max_sancion': dias_max_sancion,
        'dias_ley_aplicados': 1095,
        'metodo_calculo': 'LEGALBOT_UNIVERSAL_V2'
    }


@router.post(
    "/legal/validate",
    summary="LegalBot Universal - Validación Legal",
    description="Valida cualquier RUC usando el algoritmo LegalBot Universal V2.0 basado en Ley 30225."
)
async def legalbot_validate(
    ruc: str,
    volumen: float = 0,
    db: Session = Depends(get_db)
):
    """
    Endpoint LegalBot Universal.
    
    - **ruc**: RUC a validar (11 dígitos)
    - **volumen**: Volumen anual en soles (opcional, para determinar Founder)
    
    Returns score, tier, fecha de desbloqueo, y flags de verificación.
    """
    # Validar RUC
    if len(ruc) != 11 or not ruc.isdigit():
        return {
            "error": True,
            "message": "RUC debe tener 11 dígitos numéricos"
        }
    
    # Obtener datos SUNAT
    sunat_data = call_factiliza_api(ruc, db)
    if not sunat_data.get("success"):
        sunat_data = call_apiperu_dev(ruc, db)
    if not sunat_data.get("success"):
        sunat_data = call_peru_api(ruc, db)
    if not sunat_data.get("success"):
        sunat_data = call_buscaruc_api(ruc, db)
    
    # Obtener sanciones desde DB
    from app.services.osce_datos_abiertos import osce_datos_abiertos
    sanciones_detalle = osce_datos_abiertos.get_sanciones_detalle_from_db(ruc)
    
    # Si no hay en DB detallada, obtener desde scraping service
    if not sanciones_detalle:
        sanciones_scraping = scraping_service.get_osce_sanctions(ruc)
        sanciones_detalle = sanciones_scraping
    
    # Calcular score LegalBot V3.0 Multidimensional
    resultado = calculate_legalbot_v3(sanciones_detalle, ruc)
    
    # Ajustar tier si califica para Founder (volumen > 50M y score >= 90)
    if resultado['score'] >= 90 and volumen >= 50000000:
        resultado['tier'] = 'FOUNDER'
        resultado['es_founder_eligible'] = True
    else:
        resultado['es_founder_eligible'] = False
    
    # Guardar auditoría si hay DB
    try:
        db.execute(text("""
            INSERT INTO legal_calculations (
                ruc, fecha_calculo, sanciones_count, score,
                tier_asignado, confianza, tiene_definitiva,
                impacto_total, detalles_json, metodo_calculo
            ) VALUES (
                :ruc, NOW(), :sanciones_count, :score,
                :tier, :confianza, :tiene_definitiva,
                :impacto_total, :detalles::jsonb, :metodo
            )
        """), {
            'ruc': ruc,
            'sanciones_count': resultado['sanciones_count'],
            'score': resultado['score'],
            'tier': resultado['tier'],
            'confianza': resultado['confianza'],
            'tiene_definitiva': resultado['tiene_definitiva'],
            'impacto_total': resultado['impacto_total'],
            'detalles': json.dumps(resultado['detalles']),
            'metodo': resultado['metodo']
        })
        db.commit()
    except Exception as e:
        print(f"[LegalBot] Error guardando auditoría: {e}")
        db.rollback()
    
    # Construir mensaje según resultado
    if resultado['tier'] == 'RECHAZADO':
        mensaje = "⛔ RECHAZADO - Sanción grave vigente. No apto para certificación."
    elif resultado['score'] >= 90:
        mensaje = "✅ GOLD disponible inmediatamente."
    elif resultado['score'] >= 70:
        mensaje = "✅ SILVER disponible. Mejorable a Gold con buena conducta."
    elif resultado['score'] >= 30:
        mensaje = "⚠️ BRONZE disponible. Sanciones detectadas con impacto moderado."
    else:
        mensaje = "❌ Riesgo elevado - No apto para certificación."
    
    return {
        "ruc": ruc,
        "razon_social": sunat_data.get("razon_social", "No disponible"),
        "score": resultado['score'],
        "tier": resultado['tier'],
        "status": resultado['status'],
        "confianza": resultado['confianza'],
        "tiene_definitiva": resultado['tiene_definitiva'],
        "impacto_total": resultado['impacto_total'],
        "sanciones_count": resultado['sanciones_count'],
        "detalles": resultado['detalles'],
        "es_founder_eligible": resultado.get('es_founder_eligible', False),
        "metodo_calculo": resultado['metodo'],
        "mensaje": mensaje
    }


@router.get(
    "/legal/validate/{ruc}",
    summary="LegalBot Universal - Validación Legal (GET)",
    description="Valida cualquier RUC usando GET para compatibilidad."
)
async def legalbot_validate_get(
    ruc: str,
    volumen: float = 0,
    db: Session = Depends(get_db)
):
    """GET version del endpoint LegalBot."""
    return await legalbot_validate(ruc, volumen, db)


# Deploy force Fri Mar 28 03:30:00 AM CST 2026 - LegalBot Universal V2.0


@router.get(
    "/debug/consulta-fuentes/{ruc}",
    summary="Debug - Probar todas las fuentes de datos",
    description="Endpoint de debug para verificar qué fuentes de datos funcionan para un RUC."
)
async def debug_consulta_fuentes(ruc: str, db: Session = Depends(get_db)):
    """Debug endpoint para probar todas las fuentes de datos."""
    resultados = {}
    
    # Probar Factiliza
    try:
        f = call_factiliza_api(ruc, db)
        resultados['factiliza'] = {
            'success': f.get('success', False),
            'razon_social': f.get('razon_social', '')[:50],
            'fuente': f.get('fuente')
        }
    except Exception as e:
        resultados['factiliza'] = {'error': str(e)}
    
    # Probar apis.net.pe
    try:
        a = call_apis_net_pe(ruc, db)
        resultados['apis_net_pe'] = {
            'success': a.get('success', False),
            'razon_social': a.get('razon_social', '')[:50],
            'fuente': a.get('fuente')
        }
    except Exception as e:
        resultados['apis_net_pe'] = {'error': str(e)}
    
    # Probar APIPeru.dev
    try:
        ap = call_apiperu_dev(ruc, db)
        resultados['apiperu_dev'] = {
            'success': ap.get('success', False),
            'razon_social': ap.get('razon_social', '')[:50],
            'fuente': ap.get('fuente')
        }
    except Exception as e:
        resultados['apiperu_dev'] = {'error': str(e)}
    
    # Probar Perú API
    try:
        p = call_peru_api(ruc, db)
        resultados['peru_api'] = {
            'success': p.get('success', False),
            'razon_social': p.get('razon_social', '')[:50],
            'fuente': p.get('fuente')
        }
    except Exception as e:
        resultados['peru_api'] = {'error': str(e)}
    
    # Probar BuscarUC
    try:
        b = call_buscaruc_api(ruc, db)
        resultados['buscaruc'] = {
            'success': b.get('success', False),
            'razon_social': b.get('razon_social', '')[:50],
            'fuente': b.get('fuente')
        }
    except Exception as e:
        resultados['buscaruc'] = {'error': str(e)}
    
    # Probar Scraping SUNAT
    try:
        s = call_sunat_scraping(ruc, db)
        resultados['sunat_scraping'] = {
            'success': s.get('success', False),
            'razon_social': s.get('razon_social', '')[:50],
            'fuente': s.get('fuente')
        }
    except Exception as e:
        resultados['sunat_scraping'] = {'error': str(e)}
    
    return {
        "ruc": ruc,
        "resultados": resultados,
        "alguna_funciono": any(r.get('success') for r in resultados.values() if 'success' in r)
    }


@router.post(
    "/admin/add-ruc",
    summary="Admin - Agregar RUC manualmente",
    description="Permite agregar un RUC a la base de datos local cuando no está en Factiliza."
)
async def admin_add_ruc(
    ruc: str,
    razon_social: str,
    estado: str = "ACTIVO",
    condicion: str = "HABIDO",
    db: Session = Depends(get_db)
):
    """
    Agrega un RUC manualmente a la tabla ruc_cache.
    Útil cuando Factiliza no tiene el RUC pero tú sí conoces los datos.
    """
    # Validar RUC
    if len(ruc) != 11 or not ruc.isdigit():
        return {"error": True, "message": "RUC debe tener 11 dígitos numéricos"}
    
    if not razon_social or len(razon_social) < 3:
        return {"error": True, "message": "Razón social es requerida"}
    
    try:
        query = text("""
            INSERT INTO ruc_cache (ruc, razon_social, estado, condicion, fuente, updated_at)
            VALUES (:ruc, :razon_social, :estado, :condicion, 'manual', NOW())
            ON CONFLICT (ruc) DO UPDATE SET
                razon_social = EXCLUDED.razon_social,
                estado = EXCLUDED.estado,
                condicion = EXCLUDED.condicion,
                fuente = 'manual',
                updated_at = NOW()
            RETURNING ruc, razon_social
        """)
        
        result = db.execute(query, {
            "ruc": ruc,
            "razon_social": razon_social.upper(),
            "estado": estado.upper(),
            "condicion": condicion.upper()
        }).fetchone()
        
        db.commit()
        
        return {
            "success": True,
            "message": "RUC agregado/actualizado correctamente",
            "ruc": result[0],
            "razon_social": result[1]
        }
        
    except Exception as e:
        db.rollback()
        return {"error": True, "message": f"Error al agregar RUC: {str(e)}"}


@router.get(
    "/admin/list-ruc-cache",
    summary="Admin - Listar RUCs en caché",
    description="Lista todos los RUCs almacenados en la tabla ruc_cache."
)
async def admin_list_ruc_cache(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Lista los RUCs almacenados en caché."""
    try:
        query = text("""
            SELECT ruc, razon_social, estado, fuente, created_at
            FROM ruc_cache
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {"limit": limit}).fetchall()
        
        return {
            "success": True,
            "count": len(results),
            "rucs": [
                {
                    "ruc": r[0],
                    "razon_social": r[1],
                    "estado": r[2],
                    "fuente": r[3],
                    "created_at": str(r[4])
                }
                for r in results
            ]
        }
        
    except Exception as e:
        return {"error": True, "message": str(e)}
