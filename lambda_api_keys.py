import json
import boto3
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from decimal import Decimal

# DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('API_KEYS_TABLE', 'conflictzero-api-keys'))

def get_cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization,X-API-Key'
    }

def generate_api_key():
    """Genera API key segura"""
    prefix = 'cz_live_' if os.environ.get('ENV') == 'production' else 'cz_test_'
    key = secrets.token_urlsafe(32)
    return prefix + key

def hash_key(key):
    """Hash para almacenar en DB"""
    return hashlib.sha256(key.encode()).hexdigest()

def create_api_key(event):
    """Crea nueva API key para cliente B2B"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        client_name = body.get('client_name')
        client_email = body.get('client_email')
        plan = body.get('plan', 'starter')  # starter, pro, enterprise
        
        if not client_name or not client_email:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Nombre y email requeridos'})}
        
        # Generar key
        api_key = generate_api_key()
        key_hash = hash_key(api_key)
        
        # Límites según plan
        limits = {
            'starter': {'daily_requests': 100, 'monthly_requests': 1000},
            'pro': {'daily_requests': 1000, 'monthly_requests': 10000},
            'enterprise': {'daily_requests': 10000, 'monthly_requests': 100000}
        }
        
        # Guardar en DynamoDB
        item = {
            'key_hash': key_hash,
            'client_name': client_name,
            'client_email': client_email,
            'plan': plan,
            'api_key_prefix': api_key[:12] + '...',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=365)).isoformat(),
            'is_active': True,
            'limits': limits.get(plan, limits['starter']),
            'usage': {
                'today': 0,
                'this_month': 0,
                'total': 0
            },
            'webhook_url': body.get('webhook_url', ''),
            'notifications_enabled': body.get('notifications', True)
        }
        
        table.put_item(Item=item)
        
        return {
            'statusCode': 201,
            'headers': get_cors_headers(),
            'body': json.dumps({
                'success': True,
                'api_key': api_key,  # Solo se muestra una vez
                'client_id': key_hash[:16],
                'plan': plan,
                'limits': limits.get(plan),
                'expires_at': item['expires_at'],
                'message': 'Guarde esta API key, no se mostrará de nuevo'
            })
        }
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def validate_api_key(api_key):
    """Valida API key y retorna datos del cliente"""
    try:
        key_hash = hash_key(api_key)
        response = table.get_item(Key={'key_hash': key_hash})
        
        item = response.get('Item')
        if not item:
            return None, 'API key inválida'
        
        if not item.get('is_active'):
            return None, 'API key desactivada'
        
        if datetime.fromisoformat(item['expires_at']) < datetime.now():
            return None, 'API key expirada'
        
        # Check limits
        limits = item.get('limits', {})
        usage = item.get('usage', {})
        
        if usage.get('today', 0) >= limits.get('daily_requests', 100):
            return None, 'Límite diario excedido'
        
        return item, None
        
    except Exception as e:
        return None, str(e)

def update_usage(key_hash):
    """Incrementa contador de uso"""
    try:
        table.update_item(
            Key={'key_hash': key_hash},
            UpdateExpression='SET usage.today = if_not_exists(usage.today, :zero) + :inc, usage.this_month = if_not_exists(usage.this_month, :zero) + :inc, usage.total = if_not_exists(usage.total, :zero) + :inc',
            ExpressionAttributeValues={':inc': 1, ':zero': 0}
        )
    except Exception as e:
        print(f"Error actualizando uso: {e}")

def get_api_keys(event):
    """Lista todas las API keys (admin)"""
    try:
        response = table.scan()
        items = response.get('Items', [])
        
        # Sanitizar - no mostrar hashes completos
        keys = [{
            'client_id': item['key_hash'][:16] + '...',
            'client_name': item['client_name'],
            'client_email': item['client_email'],
            'plan': item['plan'],
            'is_active': item['is_active'],
            'created_at': item['created_at'],
            'expires_at': item['expires_at'],
            'usage': item.get('usage', {})
        } for item in items]
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'keys': keys, 'total': len(keys)})
        }
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def revoke_api_key(event):
    """Revoca una API key"""
    try:
        path_params = event.get('pathParameters', {}) or {}
        key_id = path_params.get('key_id')
        
        if not key_id:
            return {'statusCode': 400, 'body': json.dumps({'error': 'key_id requerido'})}
        
        # Buscar por prefijo
        response = table.scan(
            FilterExpression='begins_with(key_hash, :prefix)',
            ExpressionAttributeValues={':prefix': key_id}
        )
        
        items = response.get('Items', [])
        if not items:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Key no encontrada'})}
        
        # Desactivar
        table.update_item(
            Key={'key_hash': items[0]['key_hash']},
            UpdateExpression='SET is_active = :val',
            ExpressionAttributeValues={':val': False}
        )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'success': True, 'message': 'API key revocada'})
        }
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def lambda_handler(event, context):
    """Router principal"""
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': get_cors_headers(), 'body': json.dumps({'ok': True})}
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    try:
        if method == 'POST' and '/api-keys' in path:
            return create_api_key(event)
        elif method == 'GET' and '/api-keys' in path:
            return get_api_keys(event)
        elif method == 'DELETE' and '/api-keys' in path:
            return revoke_api_key(event)
        else:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Endpoint no encontrado'})}
            
    except Exception as e:
        return {'statusCode': 500, 'headers': get_cors_headers(), 'body': json.dumps({'error': str(e)})}
