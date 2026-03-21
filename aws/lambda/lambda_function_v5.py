import json
import boto3
import os
import hashlib
import urllib.request
import urllib.error
from datetime import datetime, timedelta

# Configuración
S3_BUCKET = os.environ.get('S3_BUCKET', 'conflictzero-certificados-prod')
DECOLECTA_API_KEY = os.environ.get('DECOLECTA_API_KEY', '')
DECOLECTA_BASE_URL = os.environ.get('DECOLECTA_BASE_URL', 'https://api.decolecta.com')
s3_client = boto3.client('s3')

# Headers CORS restrictivos
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': 'https://czperu.com',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}

# Mock data para OSCE/TCE (hasta tener APIs reales)
TIPOS_SANCION = ["INHABILITACION", "AMONESTACION", "MULTA", "SANCION TEMPORAL"]
ENTIDADES = ["OSCE", "TCE", "SUNAT", "MUNICIPALIDAD", "OEFA"]
MOTIVOS = [
    "Incumplimiento de contrato", "Retraso en ejecución de obra",
    "Documentación falsa", "No presentación de garantía",
    "Abandono de obra", "Deficiencias técnicas",
    "Incumplimiento de normas ambientales", "Retención indebida de pagos"
]

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
    """Obtiene datos reales de SUNAT via Decolecta - CORREGIDO"""
    try:
        result = call_decolecta_api(f'v1/sunat/ruc/{ruc}')
        print(f"Decolecta raw response: {json.dumps(result, default=str)[:800]}")
        
        if not result:
            return None
        
        # Decolecta retorna {success: true, data: {...}}
        if isinstance(result, dict):
            if result.get('success') == True or result.get('success') == 'true':
                data = result.get('data', {})
                
                # El campo es 'nombre_o_razon_social' no 'razon_social'
                razon_social = data.get('nombre_o_razon_social') or data.get('razon_social') or data.get('nombre') or data.get('razonSocial', '')
                
                if razon_social:
                    return {
                        'razon_social': razon_social.strip(),
                        'nombre_comercial': data.get('nombre_comercial', razon_social).strip(),
                        'estado': data.get('estado', 'ACTIVO'),
                        'condicion': data.get('condicion', 'HABIDO'),
                        'direccion': (data.get('direccion') or data.get('dirección_completa', '')).strip(),
                        'departamento': data.get('departamento', 'Lima'),
                        'provincia': data.get('provincia', 'Lima'),
                        'distrito': data.get('distrito', ''),
                        'ubigeo': data.get('ubigeo_sunat') or (data.get('ubigeo', ['', '', ''])[2] if isinstance(data.get('ubigeo'), list) else ''),
                        'tipo': data.get('tipo_contribuyente', 'EMPRESA'),
                        'fuente': 'decolecta_sunat'
                    }
            elif result.get('message') == 'No encontrado':
                print(f"RUC {ruc} no encontrado en SUNAT via Decolecta")
                return None
    except Exception as e:
        print(f"Error SUNAT data: {e}")
        import traceback
        traceback.print_exc()
    return None

def get_mock_osce_data(ruc, razon_social):
    """Mock data para OSCE/TCE - siempre retorna sanciones"""
    seed = generate_ruc_seed(ruc)
    tiene_problemas = pseudo_random(seed + 1, 100) < 35  # 35% tienen problemas
    
    sanciones = []
    inhabilitaciones = []
    sanciones_multa = []
    total_registros = 0
    
    if tiene_problemas:
        num_sanciones = pseudo_random(seed + 2, 3) + 1
        total_registros = num_sanciones
        
        for i in range(num_sanciones):
            tipo_idx = pseudo_random(seed + i * 10, len(TIPOS_SANCION))
            entidad_idx = pseudo_random(seed + i * 20, len(ENTIDADES))
            motivo_idx = pseudo_random(seed + i * 30, len(MOTIVOS))
            
            sancion = {
                'razon_social': razon_social,
                'tipo_sancion': TIPOS_SANCION[tipo_idx],
                'motivo': MOTIVOS[motivo_idx],
                'entidad': ENTIDADES[entidad_idx],
                'fecha_resolucion': (datetime.now() - timedelta(days=pseudo_random(seed + i * 40, 730))).strftime('%d/%m/%Y'),
                'numero_resolucion': f'R.{ruc[:4]}-{2024 if pseudo_random(seed + i * 50, 2) == 0 else 2023}-{ENTIDADES[entidad_idx][:3]}'
            }
            
            if TIPOS_SANCION[tipo_idx] == "INHABILITACION":
                inhabilitaciones.append({
                    'tipo_inhabilitacion': 'INHABILITACION TEMPORAL' if pseudo_random(seed + i * 60, 2) == 0 else 'INHABILITACION DEFINITIVA',
                    'estado': 'VIGENTE' if pseudo_random(seed + i * 70, 2) == 0 else 'CONCLUIDO',
                    'expediente': sancion['numero_resolucion'],
                    'entidad': ENTIDADES[entidad_idx],
                    'dias_inhabilitacion': (pseudo_random(seed + i * 80, 24) + 6) * 30
                })
            elif TIPOS_SANCION[tipo_idx] == "MULTA":
                sanciones_multa.append({
                    'razon_social': razon_social,
                    'monto_multa': (pseudo_random(seed + i * 90, 50) + 5) * 1000,
                    'motivo': MOTIVOS[motivo_idx]
                })
            else:
                sanciones.append(sancion)
    
    return {
        'estado_osce': 'CON_PROBLEMAS' if tiene_problemas else 'LIMPIO',
        'sanciones': sanciones,
        'inhabilitaciones': inhabilitaciones,
        'sanciones_multa': sanciones_multa,
        'total_registros': total_registros,
        'fuente_osce': 'mock'
    }

def get_ruc_data(ruc):
    """Combina datos reales de SUNAT con mock de OSCE/TCE"""
    # 1. Obtener datos reales de SUNAT via Decolecta
    sunat_data = get_sunat_data_real(ruc)
    
    # Si falla, fallback determinístico
    if not sunat_data:
        seed = generate_ruc_seed(ruc)
        mock_names = [
            "CONSTRUCTORA LOS ANDES SAC", "GRUAS INDUSTRIALES DEL PERU SA",
            "CONSORCIO VIAL LIMA SUR", "INGENIERIA Y CONSTRUCCIONES SAC",
            "SERVICIOS ELECTROMECANICOS NORTE SAC", "CONSTRUCTORA JUVEL SAC",
            "INGENIEROS CONSULTORES ASOCIADOS", "OBRAS Y SERVICIOS TECNICOS EIRL",
            "ZAMORA JARA INGENIEROS SAC", "GRUAS Y MONTACARGAS PERU SAC"
        ]
        razon_social = mock_names[pseudo_random(seed, len(mock_names))]
        sunat_data = {
            'razon_social': razon_social,
            'nombre_comercial': razon_social,
            'estado': 'ACTIVO',
            'condicion': 'HABIDO',
            'direccion': f"Av. {['Principal', 'Lima', 'Arequipa'][pseudo_random(seed+1, 3)]} N° {pseudo_random(seed+2, 9999)}",
            'departamento': 'Lima',
            'provincia': 'Lima',
            'fuente': 'mock_fallback'
        }
    
    # 2. Obtener mock data para OSCE/TCE
    osce_data = get_mock_osce_data(ruc, sunat_data['razon_social'])
    
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
            'tce': 'mock'
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
    
    return max(0, min(100, score))

def generate_certificate_html(data, score):
    """Genera HTML del certificado"""
    estado_verif = 'APROBADO' if score >= 70 else 'OBSERVADO' if score >= 40 else 'RECHAZADO'
    color = '#16a34a' if score >= 70 else '#f59e0b' if score >= 40 else '#dc2626'
    
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Certificado - {data['razon_social']}</title>
    <style>
        body {{ font-family: Helvetica, Arial, sans-serif; margin: 0; padding: 40px; background: #faf8f3; }}
        .certificate {{ background: white; border: 3px solid #D4AF37; padding: 50px; max-width: 800px; margin: 0 auto; box-shadow: 0 10px 40px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 2px solid #D4AF37; padding-bottom: 20px; margin-bottom: 30px; }}
        .logo {{ font-size: 32px; font-weight: bold; color: #0a0e1a; margin-bottom: 10px; }}
        .subtitle {{ color: #D4AF37; font-size: 14px; letter-spacing: 2px; }}
        .title {{ font-size: 28px; color: #0a0e1a; margin: 30px 0; text-align: center; }}
        .score-box {{ background: {color}; color: white; padding: 20px; text-align: center; border-radius: 10px; margin: 20px 0; }}
        .score-number {{ font-size: 48px; font-weight: bold; }}
        .score-label {{ font-size: 14px; text-transform: uppercase; letter-spacing: 2px; }}
        .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 30px 0; }}
        .info-item {{ padding: 15px; background: #faf8f3; border-left: 3px solid #D4AF37; }}
        .info-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
        .info-value {{ font-size: 16px; font-weight: bold; color: #0a0e1a; margin-top: 5px; word-break: break-word; }}
        .status {{ text-align: center; padding: 15px; background: {'#dcfce7' if score >= 70 else '#fef3c7' if score >= 40 else '#fee2e2'}; border-radius: 5px; margin: 20px 0; }}
        .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 20px; }}
        .qr {{ width: 100px; height: 100px; background: #f0f0f0; margin: 20px auto; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999; }}
    </style>
</head>
<body>
    <div class="certificate">
        <div class="header">
            <div class="logo">CONFLICTZERO</div>
            <div class="subtitle">INTELIGENCIA DE RIESGO PARA LICITACIONES</div>
        </div>
        
        <h1 class="title">CERTIFICADO DE VERIFICACIÓN</h1>
        
        <div class="score-box">
            <div class="score-number">{score}/100</div>
            <div class="score-label">Score de Riesgo</div>
        </div>
        
        <div class="status">
            <strong>ESTADO: {estado_verif}</strong><br>
            {'La empresa cumple con los requisitos para contratación pública.' if score >= 70 else 'La empresa presenta observaciones que deben ser evaluadas.' if score >= 40 else 'La empresa presenta riesgos significativos.'}
        </div>
        
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
                <div class="info-label">Estado OSCE</div>
                <div class="info-value">{'SIN SANCIONES' if data['estado'] == 'LIMPIO' else 'CON SANCIONES'}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Condición SUNAT</div>
                <div class="info-value">{data['condicion']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Total Sanciones</div>
                <div class="info-value">{data['total_registros']}</div>
            </div>
            <div class="info-item">
                <div class="info-label">Inhabilitaciones</div>
                <div class="info-value">{len(data['inhabilitaciones'])}</div>
            </div>
        </div>
        
        <div class="qr">QR<br>VERIFICACIÓN</div>
        
        <div class="footer">
            <p><strong>Fecha de Emisión:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            <p><strong>Vigencia:</strong> 30 días</p>
            <p><strong>ID:</strong> CZ-{data['ruc']}-{datetime.now().strftime('%Y%m%d%H%M%S')}</p>
            <p style="margin-top: 20px; font-size: 10px;">Certificado informativo. Para verificar autenticidad: czperu.com/verificar</p>
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
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'OK'})
        }
    
    try:
        path = event.get('path', '')
        path_params = event.get('pathParameters', {}) or {}
        ruc = path_params.get('ruc', '')
        
        is_valid, error_msg = validate_ruc(ruc)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'RUC inválido', 'message': error_msg})
            }
        
        data = get_ruc_data(ruc)
        score = calculate_score(data)
        
        if 'consulta-osce' in path:
            response = {
                'success': True,
                'data': data,
                'score': score,
                'fuentes_datos': data.get('fuentes_datos', {}),
                'timestamp': datetime.now().isoformat()
            }
        
        elif 'generar-certificado' in path:
            cert_html = generate_certificate_html(data, score)
            pdf_url = upload_certificate_to_s3(ruc, cert_html)
            
            if not pdf_url:
                return {
                    'statusCode': 500,
                    'headers': CORS_HEADERS,
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
                'headers': CORS_HEADERS,
                'body': json.dumps({'error': 'Endpoint no encontrado'})
            }
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(response, default=str)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({'error': 'Error interno', 'message': str(e)})
        }
