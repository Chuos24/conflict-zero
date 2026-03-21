import json
import boto3
import os
from datetime import datetime

sns_client = boto3.client('sns')
ses_client = boto3.client('ses')
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN', '')

def get_cors_headers():
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'POST, OPTIONS'
    }

def send_alert(event):
    """Envía alerta de riesgo alto"""
    try:
        body = json.loads(event.get('body', '{}'))
        
        ruc = body.get('ruc')
        razon_social = body.get('razon_social', 'No especificado')
        score = body.get('score', 0)
        sanciones = body.get('sanciones', [])
        email = body.get('email')  # Email del usuario a notificar
        
        if not ruc:
            return {'statusCode': 400, 'body': json.dumps({'error': 'RUC requerido'})}
        
        # Construir mensaje
        message = f"""
🚨 ALERTA DE RIESGO - Conflict Zero

Empresa: {razon_social}
RUC: {ruc}
Score de Riesgo: {score}/100
Nivel: {'CRÍTICO' if score < 40 else 'ALTO'}

Sanciones detectadas:
"""
        
        for sancion in sanciones[:5]:  # Max 5 sanciones
            message += f"\n- {sancion.get('entidad', 'N/A')}: {sancion.get('tipo_sancion', 'Sanción')}"
        
        message += f"\n\nVerificación realizada el: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        message += "\nhttps://czperu.com"
        
        # Enviar SNS
        if SNS_TOPIC_ARN:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject=f'🚨 Alerta Riesgo: {razon_social[:30]}',
                Message=message
            )
        
        # Enviar email directo si se proporcionó
        if email and score < 40:  # Solo para riesgo crítico
            ses_client.send_email(
                Source='alertas@czperu.com',
                Destination={'ToAddresses': [email]},
                Message={
                    'Subject': {'Data': f'Alerta de Riesgo: {razon_social}'},
                    'Body': {'Text': {'Data': message}}
                }
            )
        
        return {
            'statusCode': 200,
            'headers': get_cors_headers(),
            'body': json.dumps({'success': True, 'message': 'Alerta enviada'})
        }
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def subscribe_alert(event):
    """Suscribe email a alertas"""
    try:
        body = json.loads(event.get('body', '{}'))
        email = body.get('email')
        ruc_filter = body.get('ruc_filter', [])  # Lista de RUCs a monitorear
        
        if not email:
            return {'statusCode': 400, 'body': json.dumps({'error': 'Email requerido'})}
        
        # Suscribir a SNS
        if SNS_TOPIC_ARN:
            response = sns_client.subscribe(
                TopicArn=SNS_TOPIC_ARN,
                Protocol='email',
                Endpoint=email
            )
            
            return {
                'statusCode': 200,
                'headers': get_cors_headers(),
                'body': json.dumps({
                    'success': True,
                    'subscription_arn': response['SubscriptionArn'],
                    'message': 'Revisa tu email para confirmar la suscripción'
                })
            }
        
        return {'statusCode': 500, 'body': json.dumps({'error': 'SNS no configurado'})}
        
    except Exception as e:
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}

def send_webhook(data, webhook_url):
    """Envía webhook a cliente B2B"""
    import urllib.request
    
    try:
        payload = json.dumps({
            'event': 'verification.completed',
            'timestamp': datetime.now().isoformat(),
            'data': data
        }).encode()
        
        req = urllib.request.Request(
            webhook_url,
            data=payload,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
            
    except Exception as e:
        print(f"Error enviando webhook: {e}")
        return False

def lambda_handler(event, context):
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': get_cors_headers(), 'body': json.dumps({'ok': True})}
    
    path = event.get('path', '')
    method = event.get('httpMethod', 'GET')
    
    try:
        if method == 'POST' and '/alerts/send' in path:
            return send_alert(event)
        elif method == 'POST' and '/alerts/subscribe' in path:
            return subscribe_alert(event)
        else:
            return {'statusCode': 404, 'body': json.dumps({'error': 'Not found'})}
            
    except Exception as e:
        return {'statusCode': 500, 'headers': get_cors_headers(), 'body': json.dumps({'error': str(e)})}
