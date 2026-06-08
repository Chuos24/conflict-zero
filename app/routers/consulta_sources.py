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
from datetime import datetime, timedelta
from typing import List, Dict, Any

settings = get_settings()

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

ENTIDAD_MULTIPLICADORES = {
    'OSCE': 1.5,      # Crítico para constructoras
    'TCE': 1.2,       # Grave pero recuperable
    'SUNAT': 0.8,     # Menor impacto si pagada
    'INDECOPI': 1.0,  # Estándar
    'DEFAULT': 1.0
}

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

def _got_name(d: dict) -> bool:
    """Check if API response has a real company name."""
    return bool(d.get("success") and d.get("razon_social", "").strip())

def get_sunat_data_cascade(ruc: str, db) -> Dict[str, Any]:
    """
    Attempts to get SUNAT data using multiple APIs in priority order.
    Returns the first successful response with a company name.
    """
    # 1. FACTALIZA - Primary source (Consultor #40648)
    result = call_factiliza_api(ruc, db)
    if _got_name(result):
        return result
    print(f"[CASCADE] Factaliza failed ({result.get('fuente')}), trying APIPeru.dev...")
    
    # 2. APIPERU.DEV - Alternative (requires token)
    result = call_apiperu_dev(ruc, db)
    if _got_name(result):
        return result
    print(f"[CASCADE] APIPeru.dev failed ({result.get('fuente')}), trying Perú API...")
    
    # 3. PERU API - Another alternative (requires token)
    result = call_peru_api(ruc, db)
    if _got_name(result):
        return result
    print(f"[CASCADE] Perú API failed ({result.get('fuente')}), trying apis.net.pe...")
    
    # 4. APIS.NET.PE - Free, always available but rate-limited
    result = call_apis_net_pe(ruc, db)
    if _got_name(result):
        return result
    print(f"[CASCADE] apis.net.pe failed ({result.get('fuente')}), using DB fallback...")
    
    # 4.5 BUSCARUC - Free SUNAT source (currently the only working source)
    result = call_buscaruc_api(ruc, db)
    if _got_name(result):
        return result
    print(f"[CASCADE] BuscarUC failed ({result.get('fuente')}), using DB fallback...")
    
    # 5. DB LOCAL FALLBACK - Last resort
    result = get_sunat_fallback(ruc, db)
    if _got_name(result):
        return result
    
    # 6. OSCE DB FALLBACK - Use OSCE sanctions data if available
    from app.services.osce_datos_abiertos import osce_datos_abiertos
    osce_data = osce_datos_abiertos.get_sanciones_from_db(ruc)
    if osce_data and osce_data.get("nombre"):
        return {
            "ruc": ruc,
            "razon_social": osce_data.get("nombre", ""),
            "nombre": osce_data.get("nombre", ""),
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
    
    # 7. MINIMAL FALLBACK - Return empty but valid structure
    return {
        "ruc": ruc,
        "razon_social": f"RUC {ruc}",
        "nombre": f"RUC {ruc}",
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

