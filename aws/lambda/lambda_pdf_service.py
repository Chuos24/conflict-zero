import json
import boto3
import os
import urllib.request
from datetime import datetime
from weasyprint import HTML, CSS
import tempfile

s3_client = boto3.client('s3')
S3_BUCKET = os.environ.get('S3_BUCKET', 'conflictzero-certificados-prod')

# Headers CORS
ALLOWED_ORIGINS = [
    'https://czperu.com',
    'https://www.czperu.com',
    'https://conflictzero-certificados-prod.s3.amazonaws.com'
]

def get_cors_headers(origin=None):
    allowed = origin if origin and origin in ALLOWED_ORIGINS else 'https://czperu.com'
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': allowed,
        'Access-Control-Allow-Methods': 'POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization'
    }

def generate_pdf_certificate(data, score):
    """Genera PDF profesional usando WeasyPrint"""
    
    estado_verif = 'APROBADO' if score >= 70 else 'OBSERVADO' if score >= 40 else 'RECHAZADO'
    fecha_emision = datetime.now().strftime('%d de %B de %Y')
    cert_id = f"CZ-{data['ruc']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Colores según score
    if score >= 80:
        color_primary = '#1a472a'
        color_accent = '#16a34a'
    elif score >= 60:
        color_primary = '#8b6914'
        color_accent = '#f59e0b'
    else:
        color_primary = '#722f37'
        color_accent = '#dc2626'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Certificado {cert_id}</title>
        <style>
            @page {{
                size: A4;
                margin: 0;
            }}
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{
                font-family: 'Georgia', serif;
                background: linear-gradient(135deg, #0d1b2a 0%, #1b263b 100%);
                min-height: 100vh;
                padding: 40px;
            }}
            .certificate {{
                background: white;
                max-width: 800px;
                margin: 0 auto;
                padding: 60px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                position: relative;
            }}
            .gold-bar {{
                height: 6px;
                background: linear-gradient(90deg, #c9a227 0%, #e8d5a3 50%, #c9a227 100%);
                margin: -60px -60px 40px -60px;
            }}
            .watermark {{
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%) rotate(-30deg);
                font-size: 100px;
                color: rgba(201,162,39,0.03);
                font-weight: bold;
                letter-spacing: 10px;
                z-index: 0;
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
                position: relative;
                z-index: 1;
            }}
            .logo {{
                font-size: 36px;
                font-weight: bold;
                color: #0d1b2a;
                letter-spacing: 4px;
                margin-bottom: 8px;
            }}
            .logo span {{ color: #c9a227; }}
            .subtitle {{
                font-size: 11px;
                letter-spacing: 3px;
                color: #666;
                text-transform: uppercase;
            }}
            .title {{
                font-size: 24px;
                color: #0d1b2a;
                text-align: center;
                margin: 30px 0 10px;
                font-weight: normal;
            }}
            .cert-id {{
                text-align: center;
                font-size: 12px;
                color: #999;
                margin-bottom: 30px;
            }}
            .score-box {{
                background: linear-gradient(135deg, {color_primary} 0%, {color_accent} 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: space-around;
                margin: 30px 0;
            }}
            .score-circle {{
                width: 120px;
                height: 120px;
                border-radius: 50%;
                border: 4px solid rgba(255,255,255,0.3);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
            }}
            .score-value {{ font-size: 42px; font-weight: bold; }}
            .score-label {{ font-size: 10px; text-transform: uppercase; opacity: 0.8; }}
            .score-status {{
                font-size: 28px;
                font-weight: bold;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 30px 0;
            }}
            .info-item {{
                padding: 15px;
                background: #f9f9f9;
                border-left: 3px solid #c9a227;
            }}
            .info-label {{
                font-size: 10px;
                text-transform: uppercase;
                color: #999;
                margin-bottom: 5px;
            }}
            .info-value {{
                font-size: 16px;
                color: #0d1b2a;
                font-weight: 500;
            }}
            .footer {{
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #eee;
                display: flex;
                justify-content: space-between;
                font-size: 11px;
                color: #666;
            }}
            .disclaimer {{
                margin-top: 30px;
                padding: 15px;
                background: #fef9e7;
                border-left: 3px solid #f39c12;
                font-size: 10px;
                color: #856404;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="certificate">
            <div class="gold-bar"></div>
            <div class="watermark">CZ</div>
            
            <div class="header">
                <div class="logo">CONFLICT<span>ZERO</span></div>
                <div class="subtitle">Inteligencia de Riesgo para Contrataciones</div>
            </div>
            
            <h1 class="title">Certificado de Verificación de Proveedor</h1>
            <p class="cert-id">ID: {cert_id}</p>
            
            <div class="score-box">
                <div class="score-circle">
                    <div class="score-value">{score}</div>
                    <div class="score-label">Score</div>
                </div>
                <div class="score-status">{estado_verif}</div>
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
                    <div class="info-label">Estado SUNAT</div>
                    <div class="info-value">{data.get('estado_sunat', 'ACTIVO')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Sanciones</div>
                    <div class="info-value">{data.get('total_registros', 0)} registros</div>
                </div>
            </div>
            
            <div class="footer">
                <div>
                    <strong>Emitido:</strong> {fecha_emision}<br>
                    <strong>Vigencia:</strong> 30 días
                </div>
                <div style="text-align: right;">
                    <strong>Verificación:</strong> czperu.com<br>
                    Documento electrónico
                </div>
            </div>
            
            <div class="disclaimer">
                <strong>Nota:</strong> Este certificado es informativo y se basa en datos públicos. 
                Conflict Zero no garantiza exhaustividad. Se recomienda verificaciones adicionales 
                antes de decisiones contractuales.
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generar PDF con WeasyPrint
    html = HTML(string=html_content)
    pdf_bytes = html.write_pdf()
    
    return pdf_bytes, cert_id

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
        # Obtener datos del body
        body = json.loads(event.get('body', '{}'))
        data = body.get('data', {})
        score = body.get('score', 0)
        
        if not data or not data.get('ruc'):
            return {
                'statusCode': 400,
                'headers': cors_headers,
                'body': json.dumps({'error': 'Datos requeridos: data.ruc'})
            }
        
        # Generar PDF
        pdf_bytes, cert_id = generate_pdf_certificate(data, score)
        
        # Subir a S3
        key = f"certificados-pdf/{cert_id}.pdf"
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=pdf_bytes,
            ContentType='application/pdf',
            ACL='public-read'
        )
        
        pdf_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{key}"
        
        return {
            'statusCode': 200,
            'headers': cors_headers,
            'body': json.dumps({
                'success': True,
                'certificado': {
                    'id': cert_id,
                    'pdf_url': pdf_url,
                    'fecha_emision': datetime.now().isoformat()
                }
            })
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
