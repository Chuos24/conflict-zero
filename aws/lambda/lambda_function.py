import json
import boto3
import os
from datetime import datetime
import urllib.request
import ssl

# Configuración
S3_BUCKET = os.environ.get('S3_BUCKET', 'conflictzero-certificados-prod')
DECOLECTA_API_KEY = os.environ.get('DECOLECTA_API_KEY', '')

# Headers CORS - Específicos para czperu.com (seguridad UHNW)
CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': 'https://czperu.com',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type,Authorization',
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains'
}

def validate_ruc(ruc):
    """Valida formato de RUC peruano (11 dígitos, empieza con 10,15,17,20)"""
    if not ruc or len(ruc) != 11:
        return False, "RUC debe tener 11 dígitos"
    if not ruc.isdigit():
        return False, "RUC solo debe contener números"
    if ruc[:2] not in ['10', '15', '17', '20']:
        return False, "RUC no válido - prefijo incorrecto"
    return True, None

def get_mock_osce_data(ruc):
    """Datos simulados de OSCE - Reemplazar con API real cuando tengas acceso"""
    # Determinista basado en RUC para consistencia
    seed = sum(int(d) for d in ruc)
    
    estados = ['ACTIVO', 'SUSPENDIDO', 'INHABILITADO', 'HISTORICO']
    estado = estados[seed % 4]
    
    return {
        'ruc': ruc,
        'razon_social': f'EMPRESA CONSTRUCTORA {ruc[:4]} S.A.C.',
        'estado_osce': estado,
        'total_sanciones': seed % 3,
        'sanciones': [] if estado == 'ACTIVO' else [
            {
                'tipo': 'INHABILITACION',
                'resolucion': f'R.{ruc[:4]}-2024-OSCE',
                'fecha': '2024-03-15',
                'dias': (seed % 365) + 30,
                'estado': 'VIGENTE'
            }
        ] if seed % 4 == 0 else [],
        'inhabilitaciones': [],
        'sanciones_multa': [],
        'ultima_actualizacion': datetime.now().isoformat()
    }

def calculate_risk_score(data):
    """Calcula score de riesgo 0-100"""
    score = 100
    
    # Penalización por estado
    if data['estado_osce'] == 'INHABILITADO':
        score -= 50
    elif data['estado_osce'] == 'SUSPENDIDO':
        score -= 30
    elif data['estado_osce'] == 'HISTORICO':
        score -= 10
    
    # Penalización por sanciones
    score -= data['total_sanciones'] * 15
    
    return max(0, min(100, score))

def get_risk_level(score):
    """Determina nivel de riesgo"""
    if score >= 80:
        return {'nivel': 'Bajo', 'color': 'verde', 'icono': '✓'}
    elif score >= 60:
        return {'nivel': 'Moderado', 'color': 'amarillo', 'icono': '!'}
    elif score >= 40:
        return {'nivel': 'Alto', 'color': 'naranja', 'icono': '⚠'}
    else:
        return {'nivel': 'Crítico', 'color': 'rojo', 'icono': '✕'}

def lambda_handler(event, context):
    """Handler principal"""
    
    # Manejar preflight CORS
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
        
        # Obtener datos
        data = get_mock_osce_data(ruc)
        score = calculate_risk_score(data)
        risk_level = get_risk_level(score)
        
        # Preparar respuesta según endpoint
        if 'consulta-osce' in path:
            response = {
                'success': True,
                'data': {
                    'ruc': data['ruc'],
                    'razon_social': data['razon_social'],
                    'estado': data['estado_osce'],
                    'condicion': 'HABIDO',
                    'score_riesgo': score,
                    'nivel_riesgo': risk_level,
                    'sanciones': {
                        'total': data['total_sanciones'],
                        'detalle': data['sanciones']
                    },
                    'inhabilitaciones': data['inhabilitaciones'],
                    'ultima_actualizacion': data['ultima_actualizacion']
                },
                'timestamp': datetime.now().isoformat()
            }
        
        elif 'generar-certificado' in path:
            cert_id = f"CZ-{ruc}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            response = {
                'success': True,
                'certificado': {
                    'id': cert_id,
                    'ruc': data['ruc'],
                    'razon_social': data['razon_social'],
                    'estado_verificacion': 'APROBADO' if score >= 60 else 'RECHAZADO',
                    'score': score,
                    'nivel_riesgo': risk_level,
                    'fecha_emision': datetime.now().isoformat(),
                    'vigencia_dias': 30,
                    'url_verificacion': f'https://czperu.com/verificar?id={cert_id}',
                    'observaciones': 'Empresa verificada sin sanciones vigentes' if score >= 80 else 'Empresa verificada con observaciones'
                },
                'timestamp': datetime.now().isoformat()
            }
        
        elif 'health' in path:
            response = {
                'status': 'healthy',
                'version': '2.0.1',
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
            'body': json.dumps(response, indent=2)
        }
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': 'Error interno',
                'message': 'Ocurrió un error al procesar la solicitud',
                'timestamp': datetime.now().isoformat()
            })
        }
