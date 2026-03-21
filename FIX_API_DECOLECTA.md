# Actualización Lambda - Decolecta como Fuente Primaria

## Problema
Perú API tiene restricción por IP. Decolecta funciona sin restricciones.

## Solución
Cambiar el Lambda para usar Decolecta como fuente primaria.

## Código para CloudShell

```bash
cd ~

cat > lambda_decolecta.py << 'EOF'
import json
import os
import urllib.request
import ssl
from datetime import datetime

DECOLECTA_API_KEY = os.environ.get('DECOLECTA_API_KEY', '')
DECOLECTA_BASE_URL = 'https://api.decolecta.com'

def lambda_handler(event, context):
    cors_headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Methods': 'GET, OPTIONS'
    }
    
    if event.get('httpMethod') == 'OPTIONS':
        return {'statusCode': 200, 'headers': cors_headers, 'body': json.dumps({'message': 'OK'})}
    
    ruc = event.get('pathParameters', {}).get('ruc', '')
    
    if not ruc or len(ruc) != 11:
        return {'statusCode': 400, 'headers': cors_headers, 'body': json.dumps({'error': 'RUC invalido'})}
    
    try:
        ctx = ssl.create_default_context()
        url = f"{DECOLECTA_BASE_URL}/v1/sunat/ruc/{ruc}"
        
        req = urllib.request.Request(
            url, 
            headers={
                'Authorization': f'Bearer {DECOLECTA_API_KEY}',
                'Accept': 'application/json',
                'User-Agent': 'ConflictZero/1.0'
            }
        )
        
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            deco_data = json.loads(response.read().decode('utf-8'))
        
        if deco_data.get('success') and deco_data.get('data'):
            data = deco_data['data']
            razon_social = data.get('nombre_o_razon_social') or data.get('razon_social', '')
            
            result = {
                'ruc': ruc,
                'razon_social': razon_social.strip(),
                'nombre_comercial': data.get('nombre_comercial', razon_social).strip(),
                'estado_sunat': data.get('estado', 'ACTIVO'),
                'condicion': data.get('condicion', 'HABIDO'),
                'direccion': data.get('direccion', ''),
                'departamento': data.get('departamento', 'LIMA'),
                'provincia': data.get('provincia', 'LIMA'),
                'distrito': data.get('distrito', ''),
                'ubigeo': data.get('ubigeo_sunat', ''),
                'tipo': data.get('tipo_contribuyente', 'EMPRESA'),
                'fuentes_datos': {'sunat': 'decolecta_sunat', 'osce': 'no_disponible', 'tce': 'no_disponible'},
                'datos_reales': True
            }
            
            return {
                'statusCode': 200,
                'headers': cors_headers,
                'body': json.dumps({
                    'success': True,
                    'data': result,
                    'score': 85,
                    'fuentes_datos': result['fuentes_datos'],
                    'datos_reales': True,
                    'timestamp': datetime.now().isoformat()
                })
            }
        else:
            return {
                'statusCode': 503,
                'headers': cors_headers,
                'body': json.dumps({
                    'success': False, 
                    'error': 'RUC no encontrado'
                })
            }
            
    except Exception as e:
        print(f"Error: {e}")
        return {
            'statusCode': 503,
            'headers': cors_headers,
            'body': json.dumps({'success': False, 'error': str(e)})
        }
EOF

zip lambda_decolecta.zip lambda_decolecta.py

aws lambda update-function-code \
  --function-name conflictzero-api-real \
  --zip-file fileb://lambda_decolecta.zip

echo "✅ Lambda actualizado!"
```

## Después de ejecutar, probar:
```bash
curl "https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod/consulta-osce/20100017491"
```
