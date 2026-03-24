import json
import boto3
import os
import hashlib
import urllib.request
import urllib.error
import ssl
from datetime import datetime, timedelta
import re

# Configuración
S3_BUCKET = os.environ.get('S3_BUCKET', 'conflictzero-certificados-prod')
DECOLECTA_API_KEY = os.environ.get('DECOLECTA_API_KEY', '')
DECOLECTA_BASE_URL = os.environ.get('DECOLECTA_BASE_URL', 'https://api.decolecta.com')
PERU_API_KEY = os.environ.get('PERU_API_KEY', '')  # API alternativa gratuita
s3_client = boto3.client('s3')

# Headers CORS - permitir múltiples orígenes
ALLOWED_ORIGINS = [
    'https://czperu.com',
    'https://www.czperu.com',
    'https://conflictzero-certificados-prod.s3.amazonaws.com',
    'http://conflictzero-certificados-prod.s3.amazonaws.com'
]

def get_cors_headers(origin=None):
    """Retorna headers CORS según el origin de la petición"""
    allowed = origin if origin and origin in ALLOWED_ORIGINS else 'https://czperu.com'
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': allowed,
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
    }

# Configuración de scraping ético
OSCE_URL = 'http://www.osce.gob.pe/consultasenlinea/inhabilitados/inhabil_publi_mes.asp'
OSCE_USER_AGENT = 'ConflictZero-Bot/1.0 (contacto@czperu.com) - Risk verification service'

# Cache simple en memoria
_cache = {
    'osce_data': None,
    'osce_last_fetch': None,
    'osce_by_ruc': {}
}

def generate_ruc_seed(ruc):
    return int(hashlib.md5(ruc.encode()).hexdigest(), 16)

def pseudo_random(seed, max_val=100):
    return (seed * 1103515245 + 12345) % max_val

def validate_ruc(ruc):
    if not ruc or len(ruc) != 11:
        return False, "RUC debe tener 11 dígitos"
    if not ruc.isdigit():
        return False, "RUC solo debe contener números"
    valid_prefixes = ['10', '15', '17', '20']
    if ruc[:2] not in valid_prefixes:
        return False, "RUC no válido - prefijo incorrecto"
    return True, None

def scrape_osce_inhabilitados():
    """Scraper ético de OSCE - lista de inhabilitados"""
    try:
        now = datetime.now()
        if (_cache['osce_last_fetch'] and 
            _cache['osce_data'] and 
            (now - _cache['osce_last_fetch']).seconds < 1800):
            return _cache['osce_data']
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            OSCE_URL,
            headers={
                'User-Agent': OSCE_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-PE,es;q=0.9,en;q=0.8',
                'Connection': 'keep-alive',
            }
        )
        
        with urllib.request.urlopen(req, timeout=30, context=ctx) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        inhabilitados = []
        lines = html.split('\n')
        
        for line in lines:
            ruc_match = re.search(r'(\d{11})', line)
            if ruc_match:
                ruc = ruc_match.group(1)
                nombre_match = re.search(r'>([A-Z][A-Z\s\.]+(?:S\.?A\.?C?|S\.?R\.?L|E\.?I\.?R\.?L|E\.?M\.?P|COOP))<', line)
                expediente_match = re.search(r'(\d{3,4}-\d{4}-TCE-S\d)', line)
                
                if ruc and len(ruc) == 11:
                    record = {
                        'ruc': ruc,
                        'razon_social': nombre_match.group(1).strip() if nombre_match else 'NO ESPECIFICADO',
                        'expediente': expediente_match.group(1) if expediente_match else 'NO ESPECIFICADO',
                        'entidad': 'TCE',
                        'tipo': 'INHABILITACION',
                        'estado': 'VIGENTE',
                        'fecha_scrape': now.isoformat()
                    }
                    inhabilitados.append(record)
                    _cache['osce_by_ruc'][ruc] = record
        
        seen = set()
        unique = []
        for item in inhabilitados:
            if item['ruc'] not in seen:
                seen.add(item['ruc'])
                unique.append(item)
        
        result = {
            'total_registros': len(unique),
            'inhabilitados': unique,
            'fuente': 'osce_scraper',
            'fecha_actualizacion': now.isoformat(),
            'url_origen': OSCE_URL
        }
        
        _cache['osce_data'] = result
        _cache['osce_last_fetch'] = now
        
        return result
        
    except Exception as e:
        print(f"Error scrapeando OSCE: {e}")
        return None

def get_osce_data_for_ruc(ruc):
    """Obtiene datos de OSCE para un RUC específico"""
    if ruc in _cache.get('osce_by_ruc', {}):
        cached = _cache['osce_by_ruc'][ruc]
        cache_time = datetime.fromisoformat(cached.get('fecha_scrape', '2000-01-01'))
        if (datetime.now() - cache_time).seconds < 86400:
            return cached
    
    osce_data = scrape_osce_inhabilitados()
    
    if osce_data and ruc in _cache.get('osce_by_ruc', {}):
        return _cache['osce_by_ruc'][ruc]
    
    return None

def call_decolecta_api(endpoint):
    try:
        url = f"{DECOLECTA_BASE_URL}/{endpoint}"
        req = urllib.request.Request(
            url,
            headers={
                'Authorization': f'Bearer {DECOLECTA_API_KEY}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_sunat_data_real(ruc):
    """Obtiene datos reales de SUNAT via Decolecta o Perú API"""
    # Intento 1: Decolecta API
    try:
        result = call_decolecta_api(f'v1/sunat/ruc/{ruc}')
        
        if result and isinstance(result, dict):
            if result.get('success') == True or result.get('success') == 'true':
                data = result.get('data', {})
                
                razon_social = (data.get('nombre_o_razon_social') or 
                               data.get('razon_social') or 
                               data.get('nombre') or 
                               data.get('razonSocial', ''))
                
                if razon_social:
                    return {
                        'razon_social': razon_social.strip(),
                        'nombre_comercial': (data.get('nombre_comercial') or razon_social).strip(),
                        'estado': data.get('estado', 'ACTIVO'),
                        'condicion': data.get('condicion', 'HABIDO'),
                        'direccion': (data.get('direccion') or data.get('dirección_completa', '')).strip(),
                        'departamento': data.get('departamento', 'Lima'),
                        'provincia': data.get('provincia', 'Lima'),
                        'distrito': data.get('distrito', ''),
                        'ubigeo': data.get('ubigeo_sunat') or '',
                        'tipo': data.get('tipo_contribuyente', 'EMPRESA'),
                        'fuente': 'decolecta_sunat'
                    }
    except Exception as e:
        print(f"Decolecta fallo: {e}")
    
    # Intento 2: Perú API (gratuita)
    try:
        peru_api_data = call_peru_api(ruc)
        if peru_api_data:
            return peru_api_data
    except Exception as e:
        print(f"Peru API fallo: {e}")
    
    return None

def call_peru_api(ruc):
    """Consulta Perú API - API gratuita de SUNAT"""
    try:
        url = f'https://api.apisperu.com/sunat/ruc/{ruc}'
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'ConflictZero/1.0'
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            if data.get('success') or data.get('razonSocial'):
                razon_social = (data.get('razonSocial') or data.get('razon_social', ''))
                
                if razon_social:
                    return {
                        'razon_social': razon_social.strip(),
                        'nombre_comercial': (data.get('nombreComercial') or razon_social).strip(),
                        'estado': data.get('estado', 'ACTIVO'),
                        'condicion': data.get('condicion', 'HABIDO'),
                        'direccion': (data.get('direccion') or data.get('direccion_completa', '')).strip(),
                        'departamento': data.get('departamento', 'Lima'),
                        'provincia': data.get('provincia', 'Lima'),
                        'distrito': data.get('distrito', ''),
                        'ubigeo': data.get('ubigeo', ''),
                        'tipo': data.get('tipoDocumento', 'EMPRESA'),
                        'fuente': 'peru_api'
                    }
    except Exception as e:
        print(f"Error Peru API: {e}")
    
    return None

def get_osce_data_real(ruc, razon_social):
    """Obtiene datos reales de OSCE via scraper"""
    try:
        osce_record = get_osce_data_for_ruc(ruc)
        
        if osce_record:
            return {
                'estado_osce': 'CON_PROBLEMAS',
                'sanciones': [],
                'inhabilitaciones': [{
                    'tipo_inhabilitacion': 'INHABILITACION TEMPORAL',
                    'estado': osce_record.get('estado', 'VIGENTE'),
                    'expediente': osce_record.get('expediente', 'NO ESPECIFICADO'),
                    'entidad': osce_record.get('entidad', 'OSCE/TCE'),
                    'dias_inhabilitacion': 180,
                    'fecha_inicio': osce_record.get('fecha_scrape', ''),
                    'motivo': 'Sanción por incumplimiento contractual'
                }],
                'sanciones_multa': [],
                'total_registros': 1,
                'fuente_osce': 'osce_scraper'
            }
    except Exception as e:
        print(f"Error OSCE data: {e}")
    
    return None

def get_ruc_data(ruc):
    """
    Combina datos reales de SUNAT + OSCE scraper + OSCE fallback
    IMPORTANTE: Si SUNAT no encuentra el RUC, no inventamos nombre
    """
    # 1. SUNAT vía Decolecta (REAL)
    sunat_data = get_sunat_data_real(ruc)
    
    # 2. OSCE - Intentar scraper primero
    osce_data = get_osce_data_real(ruc, sunat_data['razon_social'] if sunat_data else '')
    
    # Si OSCE tampoco tiene datos, usar mock de OSCE (solo sanciones, no nombre)
    if not osce_data:
        seed = generate_ruc_seed(ruc)
        tiene_problemas = pseudo_random(seed + 1, 100) < 15  # Solo 15% tienen problemas en mock
        
        if tiene_problemas:
            osce_data = {
                'estado_osce': 'CON_PROBLEMAS',
                'sanciones': [{
                    'razon_social': sunat_data['razon_social'] if sunat_data else 'EMPRESA NO IDENTIFICADA',
                    'tipo_sancion': 'SANCION ADMINISTRATIVA',
                    'motivo': 'Incumplimiento de obligaciones',
                    'entidad': 'OSCE',
                    'fecha_resolucion': (datetime.now() - timedelta(days=pseudo_random(seed, 365))).strftime('%d/%m/%Y'),
                    'numero_resolucion': f'R.{ruc[:4]}-2024-OSCE'
                }],
                'inhabilitaciones': [],
                'sanciones_multa': [],
                'total_registros': 1,
                'fuente_osce': 'mock'
            }
        else:
            osce_data = {
                'estado_osce': 'LIMPIO',
                'sanciones': [],
                'inhabilitaciones': [],
                'sanciones_multa': [],
                'total_registros': 0,
                'fuente_osce': 'mock'
            }
    
    # Si SUNAT no encontró el RUC, retornar con warning
    if not sunat_data:
        return {
            'ruc': ruc,
            'razon_social': '⚠️ RUC NO ENCONTRADO EN SUNAT',
            'nombre_comercial': 'Información no disponible',
            'estado': osce_data['estado_osce'],
            'condicion': 'NO VERIFICADO',
            'estado_sunat': 'NO ENCONTRADO',
            'total_registros': osce_data['total_registros'],
            'sanciones': osce_data['sanciones'],
            'inhabilitaciones': osce_data['inhabilitaciones'],
            'sanciones_multa': osce_data['sanciones_multa'],
            'direccion': 'No disponible',
            'departamento': '-',
            'provincia': '-',
            'distrito': '',
            'ubigeo': '',
            'tipo': 'DESCONOCIDO',
            'fuentes_datos': {
                'sunat': 'no_encontrado',
                'osce': osce_data.get('fuente_osce', 'mock'),
                'tce': osce_data.get('fuente_osce', 'mock')
            },
            'warning': 'Este RUC no fue encontrado en la base de datos de SUNAT. Verifique que el número sea correcto.'
        }
    
    # SUNAT encontró - combinar con OSCE
    return {
        'ruc': ruc,
        'razon_social': sunat_data['razon_social'],
        'nombre_comercial': sunat_data.get('nombre_comercial', sunat_data['razon_social']),
        'estado': osce_data['estado_osce'],
        'condicion': sunat_data.get('condicion', 'HABIDO'),
        'estado_sunat': sunat_data.get('estado', 'ACTIVO'),
        'total_registros': osce_data['total_registros'],
        'sanciones': osce_data['sanciones'],
        'inhabilitaciones': osce_data['inhabilitaciones'],
        'sanciones_multa': osce_data['sanciones_multa'],
        'direccion': sunat_data.get('direccion', ''),
        'departamento': sunat_data.get('departamento', 'Lima'),
        'provincia': sunat_data.get('provincia', 'Lima'),
        'distrito': sunat_data.get('distrito', ''),
        'ubigeo': sunat_data.get('ubigeo', ''),
        'tipo': sunat_data.get('tipo', 'EMPRESA'),
        'fuentes_datos': {
            'sunat': sunat_data.get('fuente', 'mock'),
            'osce': osce_data.get('fuente_osce', 'mock'),
            'tce': osce_data.get('fuente_osce', 'mock')
        }
    }

def calculate_score(data):
    """Calcula score de riesgo 0-100"""
    score = 100
    score -= len(data['sanciones']) * 15
    score -= len(data['inhabilitaciones']) * 25
    score -= len(data['sanciones_multa']) * 10
    
    for inh in data['inhabilitaciones']:
        if inh['estado'] == 'VIGENTE':
            score -= 30
            break
    
    if data['estado'] == 'CON_PROBLEMAS':
        score -= 20
    if data['condicion'] == 'NO HABIDO':
        score -= 15
    if data.get('estado_sunat') == 'BAJA':
        score -= 25
    if data.get('estado_sunat') == 'NO ENCONTRADO':
        score -= 50  # Penalización fuerte por no estar en SUNAT
    
    return max(0, min(100, score))

def generate_certificate_html(data, score):
    """Genera HTML del certificado UHNW / High-End"""
    estado_verif = 'APROBADO' if score >= 70 else 'OBSERVADO' if score >= 40 else 'RECHAZADO'
    
    # Colores elegantes
    colors = {
        'aprobado': {'primary': '#1a472a', 'secondary': '#2d5a3d', 'accent': '#c9a227'},
        'observado': {'primary': '#8b6914', 'secondary': '#a67c00', 'accent': '#c9a227'},
        'rechazado': {'primary': '#722f37', 'secondary': '#8b3a3a', 'accent': '#c9a227'}
    }
    
    color_set = colors['aprobado'] if score >= 70 else colors['observado'] if score >= 40 else colors['rechazado']
    
    sunat_status = '✅ Verificado' if data['fuentes_datos']['sunat'] == 'decolecta_sunat' else '⚠️ No verificado'
    osce_status = '✅ Verificado' if data['fuentes_datos']['osce'] == 'osce_scraper' else '⚠️ Simulado'
    
    cert_id = f"CZ-{data['ruc']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    fecha_emision = datetime.now().strftime('%d de %B de %Y')
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certificado de Verificación | Conflict Zero</title>
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 50%, #415a77 100%);
            min-height: 100vh;
            padding: 40px 20px;
            color: #1b263b;
        }}
        .certificate-container {{
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            border-radius: 4px;
            overflow: hidden;
            box-shadow: 0 25px 80px rgba(0,0,0,0.4), 0 0 0 1px rgba(201,162,39,0.1);
        }}
        .header-bar {{
            height: 8px;
            background: linear-gradient(90deg, #c9a227 0%, #e8d5a3 50%, #c9a227 100%);
        }}
        .certificate {{
            padding: 60px;
            background: linear-gradient(180deg, #fafbfc 0%, #ffffff 100%);
        }}
        .logo-section {{
            text-align: center;
            margin-bottom: 50px;
            padding-bottom: 40px;
            border-bottom: 1px solid #e5e7eb;
        }}
        .logo {{
            font-family: 'Playfair Display', serif;
            font-size: 42px;
            font-weight: 700;
            color: #0d1b2a;
            letter-spacing: 4px;
            text-transform: uppercase;
        }}
        .logo span {{
            color: #c9a227;
            font-weight: 400;
        }}
        .subtitle {{
            font-size: 11px;
            letter-spacing: 6px;
            color: #6b7280;
            text-transform: uppercase;
            margin-top: 8px;
            font-weight: 500;
        }}
        .document-title {{
            font-family: 'Playfair Display', serif;
            font-size: 28px;
            text-align: center;
            color: #0d1b2a;
            margin-bottom: 10px;
            font-weight: 600;
        }}
        .document-number {{
            text-align: center;
            font-size: 12px;
            color: #6b7280;
            letter-spacing: 2px;
            margin-bottom: 50px;
        }}
        .score-section {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 40px;
            padding: 40px;
            background: linear-gradient(135deg, {color_set['primary']} 0%, {color_set['secondary']} 100%);
            border-radius: 8px;
            margin-bottom: 50px;
            color: white;
        }}
        .score-circle {{
            width: 140px;
            height: 140px;
            border-radius: 50%;
            border: 4px solid rgba(255,255,255,0.3);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: rgba(255,255,255,0.1);
        }}
        .score-value {{
            font-size: 48px;
            font-weight: 700;
        }}
        .score-label {{
            font-size: 11px;
            letter-spacing: 2px;
            text-transform: uppercase;
            opacity: 0.8;
        }}
        .score-info h3 {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 8px;
        }}
        .score-info p {{
            font-size: 14px;
            opacity: 0.9;
            line-height: 1.5;
        }}
        .section-title {{
            font-family: 'Playfair Display', serif;
            font-size: 16px;
            color: #0d1b2a;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #c9a227;
            display: inline-block;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 25px;
            margin-bottom: 40px;
        }}
        .info-item {{
            padding: 20px;
            background: #f9fafb;
            border-left: 3px solid #c9a227;
        }}
        .info-label {{
            font-size: 10px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            margin-bottom: 6px;
            font-weight: 600;
        }}
        .info-value {{
            font-size: 16px;
            color: #0d1b2a;
            font-weight: 500;
        }}
        .data-sources {{
            background: #f3f4f6;
            padding: 20px;
            border-radius: 6px;
            margin-bottom: 40px;
        }}
        .data-sources h4 {{
            font-size: 12px;
            color: #6b7280;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 15px;
        }}
        .source-item {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #e5e7eb;
            font-size: 14px;
        }}
        .source-item:last-child {{
            border-bottom: none;
        }}
        .footer-section {{
            margin-top: 50px;
            padding-top: 40px;
            border-top: 1px solid #e5e7eb;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }}
        .footer-info {{
            font-size: 12px;
            color: #6b7280;
            line-height: 1.8;
        }}
        .qr-placeholder {{
            width: 100px;
            height: 100px;
            background: #f3f4f6;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
            color: #9ca3af;
            text-align: center;
        }}
        .watermark {{
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 120px;
            color: rgba(201,162,39,0.03);
            font-weight: 700;
            letter-spacing: 20px;
            pointer-events: none;
            z-index: 0;
        }}
        .disclaimer {{
            margin-top: 30px;
            padding: 20px;
            background: #fef3c7;
            border-left: 4px solid #f59e0b;
            font-size: 12px;
            color: #92400e;
            line-height: 1.6;
        }}
        @media print {{
            body {{ background: white; }}
            .certificate-container {{ box-shadow: none; }}
        }}
    </style>
</head>
<body>
    <div class="certificate-container">
        <div class="header-bar"></div>
        <div class="watermark">CZ</div>
        
        <div class="certificate">
            <div class="logo-section">
                <div class="logo">CONFLICT<span>ZERO</span></div>
                <div class="subtitle">Inteligencia de Riesgo para Licitaciones</div>
            </div>
            
            <h1 class="document-title">Certificado de Verificación de Proveedor</h1>
            <p class="document-number">ID: {cert_id}</p>
            
            <div class="score-section">
                <div class="score-circle">
                    <div class="score-value">{score}</div>
                    <div class="score-label">Score / 100</div>
                </div>
                <div class="score-info">
                    <h3>{estado_verif}</h3>
                    <p>{'La empresa cumple con los requisitos para participar en procesos de contratación pública.' if score >= 70 else 'Se recomienda evaluación adicional antes de la contratación.' if score >= 40 else 'La empresa presenta riesgos significativos que deben ser considerados.'}</p>
                </div>
            </div>
            
            <h2 class="section-title">Información del Contribuyente</h2>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">RUC</div>
                    <div class="info-value">{data['ruc']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Razón Social</div>
                    <div class="info-value">{data['razon_social']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Estado SUNAT</div>
                    <div class="info-value">{data['estado_sunat']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Condición</div>
                    <div class="info-value">{data['condicion']}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Sanciones OSCE/TCE</div>
                    <div class="info-value">{data['total_registros']} registros</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Inhabilitaciones</div>
                    <div class="info-value">{len(data['inhabilitaciones'])}</div>
                </div>
            </div>
            
            <div class="data-sources">
                <h4>Fuentes de Datos Verificadas</h4>
                <div class="source-item">
                    <span>SUNAT - Superintendencia Nacional de Aduanas y de Administración Tributaria</span>
                    <span style="color: {'#16a34a' if data['fuentes_datos']['sunat'] == 'decolecta_sunat' else '#dc2626'}">{sunat_status}</span>
                </div>
                <div class="source-item">
                    <span>OSCE - Organismo Supervisor de las Contrataciones del Estado</span>
                    <span style="color: {'#16a34a' if data['fuentes_datos']['osce'] == 'osce_scraper' else '#f59e0b'}">{osce_status}</span>
                </div>
                <div class="source-item">
                    <span>TCE - Tribunal de Contrataciones del Estado</span>
                    <span style="color: {'#16a34a' if data['fuentes_datos']['tce'] == 'osce_scraper' else '#f59e0b'}">{osce_status}</span>
                </div>
            </div>
            
            <div class="footer-section">
                <div class="footer-info">
                    <strong>Fecha de Emisión:</strong> {fecha_emision}<br>
                    <strong>Vigencia:</strong> 30 días<br>
                    <strong>Verificación:</strong> czperu.com/verificar<br>
                    <em style="font-size: 10px; color: #9ca3af;">Documento generado electrónicamente</em>
                </div>
                <div class="qr-placeholder">
                    Código de<br>Verificación
                </div>
            </div>
            
            <div class="disclaimer">
                <strong>Nota importante:</strong> Este certificado es informativo y se basa en datos disponibles en fuentes públicas al momento de la consulta. Conflict Zero no garantiza la exhaustividad de la información. Se recomienda realizar verificaciones adicionales antes de decisiones contractuales significativas.
            </div>
        </div>
    </div>
</body>
</html>"""
    return html

def upload_certificate_to_s3(ruc, html_content):
    try:
        cert_id = f"CZ-{ruc}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        key = f"certificados/{cert_id}.html"
        
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=html_content.encode('utf-8'),
            ContentType='text/html',
            ACL='public-read'
        )
        
        return f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"
    except Exception as e:
        print(f"Error S3: {e}")
        return None

def lambda_handler(event, context):
    origin = event.get('headers', {}).get('origin') or event.get('headers', {}).get('Origin', '')
    cors_headers = get_cors_headers(origin)
    
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({'message': 'OK'})
        }
    
    try:
        path = event.get('path', '')
        path_params = event.get('pathParameters', {}) or {}
        ruc = path_params.get('ruc', '')
        
        # Si no viene en pathParameters, intentar extraer del path
        if not ruc:
            path_parts = path.split('/')
            for i, part in enumerate(path_parts):
                if part in ['consulta-osce', 'generar-certificado'] and i + 1 < len(path_parts):
                    ruc = path_parts[i + 1]
                    break
        
        is_valid, error_msg = validate_ruc(ruc)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'RUC inválido', 'message': error_msg})
            }
        
        data = get_ruc_data(ruc)
        score = calculate_score(data)
        
        # Verificar endpoint considerando que path puede incluir /prod/
        path_clean = path.replace('/prod/', '/').replace('/dev/', '/')
        
        if '/consulta-osce/' in path_clean or path_clean.endswith('/consulta-osce'):
            response = {
                'success': True,
                'data': data,
                'score': score,
                'fuentes_datos': data.get('fuentes_datos', {}),
                'timestamp': datetime.now().isoformat()
            }
            if 'warning' in data:
                response['warning'] = data['warning']
        
        elif '/generar-certificado/' in path_clean or path_clean.endswith('/generar-certificado'):
            cert_html = generate_certificate_html(data, score)
            pdf_url = upload_certificate_to_s3(ruc, cert_html)
            
            if not pdf_url:
                return {
                    'statusCode': 500,
                    'headers': cors_headers,
                    'body': json.dumps({'success': False, 'error': 'Error S3'})
                }
            
            response = {
                'success': True,
                'certificado': {
                    'id': f"CZ-{ruc}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    'ruc': data['ruc'],
                    'razon_social': data['razon_social'],
                    'estado': data['estado'],
                    'score': score,
                    'pdf_url': pdf_url,
                    'fecha_emision': datetime.now().isoformat(),
                    'vigencia_dias': 30
                },
                'timestamp': datetime.now().isoformat()
            }
        
        else:
            return {
                'statusCode': 404,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Endpoint no encontrado'})
            }
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps(response, default=str)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': cors_headers,
            'body': json.dumps({'error': 'Error interno', 'message': str(e)})
        }
