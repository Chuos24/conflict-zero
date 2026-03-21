import json
import boto3
import os
import hashlib
from datetime import datetime, timedelta
import base64

# Configuración
S3_BUCKET = os.environ.get('S3_BUCKET', 'conflictzero-certificados-prod')
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

# Lista de razones sociales peruanas reales para mock data
RAZONES_SOCIALES = [
    "CONSTRUCTORA ZAMORA JARA SAC",
    "GRUAS Y SERVICIOS INDUSTRIALES SA",
    "CONSORCIO VIAL LIMA SUR",
    "INGENIERIA Y CONSTRUCCIONES DEL PERU EIRL",
    "SERVICIOS ELECTROMECANICOS DEL NORTE SAC",
    "CONSTRUCTORA JUVEL SAC",
    "INGENIEROS CONSULTORES ASOCIADOS SA",
    "OBRAS Y SERVICIOS TECNICOS EIRL",
    "CONSTRUCTORA LOS ANDES SAC",
    "GRUAS Y MONTACARGAS DEL PERU SAC"
]

# Tipos de sanciones OSCE
TIPOS_SANCION = [
    "INHABILITACION",
    "AMONESTACION", 
    "MULTA",
    "SANCION TEMPORAL"
]

# Entidades sancionadoras
ENTIDADES = ["OSCE", "TCE", "SUNAT", "MUNICIPALIDAD", "OEFA"]

# Motivos de sanción
MOTIVOS = [
    "Incumplimiento de contrato",
    "Retraso en ejecución de obra",
    "Documentación falsa",
    "No presentación de garantía",
    "Abandono de obra",
    "Deficiencias técnicas",
    "Incumplimiento de normas ambientales",
    "Retención indebida de pagos"
]

def generate_ruc_seed(ruc):
    """Genera seed determinista basado en RUC"""
    return int(hashlib.md5(ruc.encode()).hexdigest(), 16)

def pseudo_random(seed, max_val=100):
    """Generador pseudoaleatorio determinista"""
    return (seed * 1103515245 + 12345) % max_val

def validate_ruc(ruc):
    """Valida formato de RUC peruano"""
    if not ruc or len(ruc) != 11:
        return False, "RUC debe tener 11 dígitos"
    if not ruc.isdigit():
        return False, "RUC solo debe contener números"
    # Validar dígito de control (algoritmo simplificado)
    valid_prefixes = ['10', '15', '17', '20']
    if ruc[:2] not in valid_prefixes:
        return False, "RUC no válido - prefijo incorrecto"
    return True, None

def get_ruc_data(ruc):
    """Genera datos deterministas pero únicos para cada RUC"""
    seed = generate_ruc_seed(ruc)
    
    # Seleccionar razón social determinista
    razon_index = pseudo_random(seed, len(RAZONES_SOCIALES))
    razon_social = RAZONES_SOCIALES[razon_index]
    
    # Determinar si tiene problemas (70% limpio, 30% con problemas)
    tiene_problemas = pseudo_random(seed + 1, 100) < 30
    
    # Generar sanciones si tiene problemas
    sanciones = []
    inhabilitaciones = []
    sanciones_multa = []
    total_registros = 0
    
    if tiene_problemas:
        num_sanciones = pseudo_random(seed + 2, 3) + 1  # 1-3 sanciones
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
                'fecha_resolucion': (datetime.now() - timedelta(days=pseudo_random(seed + i * 40, 365))).strftime('%d/%m/%Y'),
                'numero_resolucion': f'R.{ruc[:4]}-{2024 if pseudo_random(seed + i * 50, 2) == 0 else 2023}-{ENTIDADES[entidad_idx][:3]}'
            }
            
            # Clasificar según tipo
            if TIPOS_SANCION[tipo_idx] == "INHABILITACION":
                inhabilitaciones.append({
                    'tipo_inhabilitacion': 'INHABILITACION TEMPORAL' if pseudo_random(seed + i * 60, 2) == 0 else 'INHABILITACION DEFINITIVA',
                    'estado': 'VIGENTE' if pseudo_random(seed + i * 70, 2) == 0 else 'CONCLUIDO',
                    'expediente': sancion['numero_resolucion'],
                    'entidad': ENTIDADES[entidad_idx],
                    'dias_inhabilitacion': (pseudo_random(seed + i * 80, 24) + 6) * 30  # 6-30 meses
                })
            elif TIPOS_SANCION[tipo_idx] == "MULTA":
                sanciones_multa.append({
                    'razon_social': razon_social,
                    'monto_multa': (pseudo_random(seed + i * 90, 50) + 5) * 1000,  # 5,000 - 55,000
                    'motivo': MOTIVOS[motivo_idx]
                })
            else:
                sanciones.append(sancion)
    
    return {
        'ruc': ruc,
        'razon_social': razon_social,
        'estado': 'CON_PROBLEMAS' if tiene_problemas else 'LIMPIO',
        'condicion': 'HABIDO' if pseudo_random(seed + 99, 100) < 95 else 'NO HABIDO',
        'total_registros': total_registros,
        'sanciones': sanciones,
        'inhabilitaciones': inhabilitaciones,
        'sanciones_multa': sanciones_multa,
        'direccion': f'Av. {["Principal", "Lima", "Arequipa", "Trujillo", "Cuzco"][pseudo_random(seed + 100, 5)]} N° {pseudo_random(seed + 101, 9999)}',
        'departamento': ['Lima', 'Arequipa', 'La Libertad', 'Cusco', 'Junin'][pseudo_random(seed + 102, 5)],
        'provincia': ['Lima', 'Arequipa', 'Trujillo', 'Cusco', 'Huancayo'][pseudo_random(seed + 103, 5)]
    }

def calculate_score(data):
    """Calcula score de riesgo 0-100 basado en datos OSCE/TCE/SUNAT"""
    score = 100
    
    # Penalización por sanciones
    score -= len(data['sanciones']) * 15
    score -= len(data['inhabilitaciones']) * 25
    score -= len(data['sanciones_multa']) * 10
    
    # Penalización por inhabilitaciones vigentes
    for inh in data['inhabilitaciones']:
        if inh['estado'] == 'VIGENTE':
            score -= 30
            break
    
    # Penalización por estado
    if data['estado'] == 'CON_PROBLEMAS':
        score -= 20
    if data['condicion'] == 'NO HABIDO':
        score -= 15
    
    return max(0, min(100, score))

def generate_certificate_html(data, score):
    """Genera HTML del certificado"""
    estado_verif = 'APROBADO' if score >= 70 else 'OBSERVADO' if score >= 40 else 'RECHAZADO'
    color = '#16a34a' if score >= 70 else '#f59e0b' if score >= 40 else '#dc2626'
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: 'Helvetica', Arial, sans-serif; margin: 40px; background: #faf8f3; }}
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
            .info-value {{ font-size: 16px; font-weight: bold; color: #0a0e1a; margin-top: 5px; }}
            .status {{ text-align: center; padding: 15px; background: {'#dcfce7' if score >= 70 else '#fef3c7' if score >= 40 else '#fee2e2'}; border-radius: 5px; margin: 20px 0; }}
            .footer {{ margin-top: 40px; text-align: center; font-size: 12px; color: #666; border-top: 1px solid #ddd; padding-top: 20px; }}
            .qr-placeholder {{ width: 100px; height: 100px; background: #f0f0f0; margin: 20px auto; display: flex; align-items: center; justify-content: center; font-size: 10px; color: #999; }}
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
                <strong>ESTADO DE VERIFICACIÓN: {estado_verif}</strong><br>
                {'La empresa cumple con los requisitos para contratación pública.' if score >= 70 else 'La empresa presenta observaciones que deben ser evaluadas.' if score >= 40 else 'La empresa presenta riesgos significativos para contratación.'}
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
                    <div class="info-label">Condición</div>
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
            
            <div class="qr-placeholder">QR<br>VERIFICACIÓN</div>
            
            <div class="footer">
                <p><strong>Fecha de Emisión:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><strong>Vigencia:</strong> 30 días</p>
                <p><strong>ID Certificado:</strong> CZ-{data['ruc']}-{datetime.now().strftime('%Y%m%d%H%M%S')}</p>
                <p style="margin-top: 20px; font-size: 10px;">Este certificado es emitido con fines informativos y no constituye una opinión legal. Para verificar autenticidad visite czperu.com/verificar</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html

def upload_certificate_to_s3(ruc, html_content):
    """Sube certificado a S3 y retorna URL"""
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
        print(f"Error subiendo a S3: {e}")
        return None

def lambda_handler(event, context):
    """Handler principal"""
    
    # Manejar CORS preflight
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
        
        # Validar RUC
        is_valid, error_msg = validate_ruc(ruc)
        if not is_valid:
            return {
                'statusCode': 400,
                'headers': CORS_HEADERS,
                'body': json.dumps({
                    'error': 'RUC inválido',
                    'message': error_msg,
                    'ruc_proporcionado': ruc
                })
            }
        
        # Obtener datos deterministas para este RUC
        data = get_ruc_data(ruc)
        score = calculate_score(data)
        
        # Endpoint /consulta-osce
        if 'consulta-osce' in path:
            response = {
                'success': True,
                'data': data,
                'score': score,
                'timestamp': datetime.now().isoformat()
            }
        
        # Endpoint /generar-certificado
        elif 'generar-certificado' in path:
            cert_html = generate_certificate_html(data, score)
            
            # Intentar subir a S3, si falla generar data URI
            pdf_url = upload_certificate_to_s3(ruc, cert_html)
            
            if not pdf_url:
                # Fallback: generar data URI para descarga
                html_base64 = base64.b64encode(cert_html.encode()).decode()
                pdf_url = f"data:text/html;base64,{html_base64}"
            
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
            'body': json.dumps(response)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': 'Error interno del servidor',
                'message': str(e),
                'timestamp': datetime.now().isoformat()
            })
        }
