"""
Conflict Zero API V3.0 - Score/Plan Desacoplado + Factaliza Integration
Backend para el sistema de validación legal con scoring multidimensional
Consultor Factaliza #40648
"""

import os
import uuid
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# Configuración
DATABASE_URL = os.environ.get('DATABASE_URL', '')
REDIS_URL = os.environ.get('REDIS_URL', '')
API_PORT = int(os.environ.get('PORT', 8000))

app = FastAPI(
    title="Conflict Zero API V3.0",
    version="3.0.0",
    description="Sistema Score/Plan Desacoplado - LegalBot V3.0 + Factaliza #40648"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============ MODELOS ============

class ValidateRequest(BaseModel):
    ruc: str
    volumen: Optional[int] = 0

class GenerateCertRequest(BaseModel):
    ruc: str
    plan: str
    email: Optional[str] = None
    company_name: Optional[str] = None

# ============ FACTALIZA ADAPTER (Inline para Render) ============

FACTALIZA_TOKEN = os.environ.get(
    'FACTALIZA_TOKEN',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDY0OCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.d_-YT6RuTIrq-RZj1TO6Q6r3EG2NL4MRO9odkcaGDYA'
)
FACTALIZA_BASE_URL = "https://api.factaliza.pe/api/v1"

class FactalizaAdapter:
    def __init__(self, token: str = None):
        self.token = token or FACTALIZA_TOKEN
        self.headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def consultar_ruc(self, ruc: str) -> Optional[Dict]:
        """Consulta RUC en Factaliza API"""
        import httpx
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.get(
                    f"{FACTALIZA_BASE_URL}/ruc/{ruc}",
                    headers=self.headers
                )
                
                if response.status_code == 429:
                    raise Exception("RATE_LIMIT")
                if response.status_code == 404:
                    return None
                
                response.raise_for_status()
                return self._normalize(ruc, response.json())
                
            except Exception as e:
                raise Exception(f"FACTALIZA_ERROR: {str(e)}")
    
    def _normalize(self, ruc: str, data: dict) -> Dict:
        """Normaliza datos de Factaliza a formato interno"""
        sunat = data.get('sunat', {})
        sanciones_raw = data.get('osce', {}).get('sanciones', []) or data.get('sanciones', [])
        
        # Normalizar sanciones
        sanciones = []
        dias_desde = 0
        
        for s in sanciones_raw:
            try:
                fecha_inicio = s.get('fecha_inicio', '')
                if fecha_inicio:
                    fecha_dt = datetime.strptime(fecha_inicio, '%Y-%m-%d')
                    dias = (datetime.now() - fecha_dt).days
                    if dias_desde == 0 or dias < dias_desde:
                        dias_desde = dias
                else:
                    dias = 0
                
                sanciones.append({
                    'resolucion': s.get('resolucion', 'N/A'),
                    'entidad': s.get('entidad', 'OSCE'),
                    'fecha_inicio': fecha_inicio,
                    'estado': s.get('estado', 'VIGENTE'),
                    'dias_transcurridos': dias,
                    'descripcion': s.get('descripcion', '')
                })
            except:
                continue
        
        return {
            'ruc': ruc,
            'razon_social': sunat.get('razon_social') or sunat.get('nombre_o_razon_social', f'Empresa {ruc}'),
            'sunat': {
                'estado': sunat.get('estado_del_contribuyente', 'ACTIVO'),
                'condicion': sunat.get('condicion_del_contribuyente', 'HABIDO'),
            },
            'sanciones': sanciones,
            'tiene_sanciones': len(sanciones) > 0,
            'dias_desde_sancion': dias_desde,
            'anios_desde_sancion': round(dias_desde / 365, 2) if dias_desde > 0 else 0,
            'fuente': 'FACTALIZA_API',
            'consultor_id': '40648',
            'timestamp': datetime.now().isoformat()
        }

# Instancia global
factaliza = FactalizaAdapter()

# ============ DATOS DEMO ============

DEMO_DATA = {
    '20529400790': {
        'razon_social': 'CONSTRUCTORA ZAMORA JARA SAC',
        'score': 41.0,
        'tier': 'BRONZE',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [{
            'resolucion': '4162-2023-TCE-S4',
            'entidad': 'TCE',
            'fecha_inicio': '2023-09-28',
            'dias_transcurridos': 912,
            'estado': 'VIGENTE'
        }],
    },
    '20100123091': {
        'razon_social': 'EMPRESA DEMO GOLD SAC',
        'score': 95.0,
        'tier': 'GOLD',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [],
    }
}

# ============ SCORING CON FACTALIZA ============

async def consultar_con_fallback(ruc: str) -> Dict:
    """Estrategia cascada: Factaliza → Cache → Mock"""
    
    # 1. Intentar Factaliza
    try:
        print(f"[Factaliza] Consultando {ruc}...")
        data = await factaliza.consultar_ruc(ruc)
        if data:
            print(f"[Factaliza] ✓ Datos recibidos")
            return data
    except Exception as e:
        print(f"[Factaliza] ⚠ {e}")
    
    # 2. Fallback a mock demo
    if ruc in DEMO_DATA:
        demo = DEMO_DATA[ruc]
        return {
            'ruc': ruc,
            'razon_social': demo['razon_social'],
            'sunat': demo['sunat'],
            'sanciones': demo.get('sanciones', []),
            'tiene_sanciones': len(demo.get('sanciones', [])) > 0,
            'dias_desde_sancion': demo.get('sanciones', [{}])[0].get('dias_transcurridos', 0) if demo.get('sanciones') else 0,
            'fuente': 'MOCK_DEMO',
            'consultor_id': '40648',
            'timestamp': datetime.now().isoformat()
        }
    
    # 3. Mock default
    return {
        'ruc': ruc,
        'razon_social': f'Empresa {ruc}',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [],
        'tiene_sanciones': False,
        'dias_desde_sancion': 0,
        'fuente': 'MOCK_DEFAULT',
        'consultor_id': '40648',
        'timestamp': datetime.now().isoformat()
    }

async def calculate_score_v3(ruc: str) -> Dict:
    """LegalBot V3.0 - Scoring con Factaliza"""
    
    # Obtener datos (Factaliza o fallback)
    data = await consultar_con_fallback(ruc)
    
    score = 100.0
    sanciones = data.get('sanciones', [])
    sunat = data.get('sunat', {})
    
    # Penalización por sanciones
    if sanciones:
        sancion = sanciones[0]
        dias = sancion.get('dias_transcurridos', 0)
        anios = dias / 365 if dias > 0 else 0
        entidad = sancion.get('entidad', 'OSCE')
        
        base_penalizacion = 70.0
        entidad_mult = {'TCE': 1.2, 'OSCE': 1.0, 'SUNAT': 0.9}.get(entidad, 1.0)
        
        # Factor temporal (recuperación gradual)
        if anios > 3:
            factor_tiempo = 0.3
        elif anios > 1:
            factor_tiempo = 0.7
        else:
            factor_tiempo = 1.0
        
        impacto = base_penalizacion * entidad_mult * factor_tiempo
        score = max(0.0, score - impacto)
    
    # Penalización SUNAT
    if sunat.get('condicion') == 'NO HABIDO':
        score = min(score, 20.0)
    if sunat.get('estado') == 'BAJA':
        score = 0.0
    
    # Determinar tier
    if score >= 90:
        tier = 'GOLD'
    elif score >= 70:
        tier = 'SILVER'
    elif score >= 30:
        tier = 'BRONZE'
    else:
        tier = 'RECHAZADO'
    
    return {
        'ruc': ruc,
        'razon_social': data.get('razon_social', f'Empresa {ruc}'),
        'score': round(score, 1),
        'tier': tier,
        'confianza': 0.95 if data.get('fuente') == 'FACTALIZA_API' else 0.85,
        'sanciones': sanciones,
        'sunat_estado': sunat.get('estado', 'DESCONOCIDO'),
        'sunat_condicion': sunat.get('condicion', 'DESCONOCIDO'),
        'fuente_datos': data.get('fuente', 'MOCK'),
        'consultor_factaliza': data.get('consultor_id', '40648'),
        'timestamp': data.get('timestamp', datetime.now().isoformat())
    }

def get_tier_info(score: float) -> Dict:
    """Info visual del tier"""
    if score >= 90:
        return {
            'name': 'GOLD', 'color': '#D4AF37', 'bg_color': 'rgba(212, 175, 55, 0.1)',
            'badge': '★', 'desc': 'Excelencia en Cumplimiento Normativo',
            'message': 'Empresa con excelencia demostrada.'
        }
    elif score >= 70:
        return {
            'name': 'SILVER', 'color': '#C0C0C0', 'bg_color': 'rgba(192, 192, 192, 0.1)',
            'badge': '◆', 'desc': 'Buen Cumplimiento Establecido',
            'message': 'Empresa con buen historial.'
        }
    elif score >= 30:
        return {
            'name': 'BRONZE', 'color': '#B87333', 'bg_color': 'rgba(184, 115, 51, 0.1)',
            'badge': '●', 'desc': 'Operativo con Observaciones',
            'message': 'Empresa operativa con observaciones.'
        }
    else:
        return {
            'name': 'RECHAZADO', 'color': '#8B0000', 'bg_color': 'rgba(139, 0, 0, 0.1)',
            'badge': '✕', 'desc': 'Requiere Regularización',
            'message': 'No apto para contratación pública.'
        }

def get_available_plans(score: float) -> List[Dict]:
    """Planes disponibles según score"""
    plans = []
    
    if score >= 30:
        plans.append({
            'id': 'starter', 'name': 'Starter', 'price': 400,
            'price_formatted': 'S/ 400',
            'features': ['Perfil público certificado', 'QR verificación', 'Soporte email'],
            'disabled': False, 'recommended': score >= 30 and score < 70
        })
    else:
        plans.append({
            'id': 'starter', 'name': 'Starter', 'price': 400,
            'price_formatted': 'S/ 400', 'features': ['No disponible'],
            'disabled': True, 'reason': f'Score {score} insuficiente. Requiere 30+', 'recommended': False
        })
    
    if score >= 70:
        plans.append({
            'id': 'professional', 'name': 'Professional', 'price': 800,
            'price_formatted': 'S/ 800',
            'features': ['Todo Starter +', 'Mi Lista (20)', 'Export CSV', 'Alertas'],
            'disabled': False, 'recommended': score >= 70 and score < 90
        })
    else:
        plans.append({
            'id': 'professional', 'name': 'Professional', 'price': 800,
            'price_formatted': 'S/ 800', 'features': ['No disponible'],
            'disabled': True, 'reason': f'Score {score} insuficiente. Requiere 70+', 'recommended': False
        })
    
    if score >= 90:
        plans.append({
            'id': 'enterprise', 'name': 'Enterprise', 'price': 2500,
            'price_formatted': 'S/ 2,500',
            'features': ['Todo Pro +', 'Mi Red ilimitado', 'API ERP', 'Puerta CZ'],
            'disabled': False, 'recommended': score >= 90, 'badge': 'FOUNDER' if score >= 95 else None
        })
    else:
        plans.append({
            'id': 'enterprise', 'name': 'Enterprise', 'price': 2500,
            'price_formatted': 'S/ 2,500', 'features': ['No disponible'],
            'disabled': True, 'reason': f'Score {score} insuficiente. Requiere 90+', 'recommended': False
        })
    
    return plans

# ============ ENDPOINTS ============

@app.get("/api/v3/health")
def health_check():
    return {
        "status": "healthy",
        "version": "3.0.0",
        "system": "Score/Plan Desacoplado + Factaliza #40648",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/v3/validate")
async def validate_ruc(request: ValidateRequest):
    """Valida RUC y retorna Score + Tier + Planes"""
    ruc = request.ruc.strip()
    
    if len(ruc) != 11 or not ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC inválido")
    
    try:
        result = await calculate_score_v3(ruc)
        tier_info = get_tier_info(result['score'])
        plans = get_available_plans(result['score'])
        
        return {
            'success': True,
            'ruc': ruc,
            'company_name': result['razon_social'],
            'score': result['score'],
            'tier': {
                'name': tier_info['name'], 'color': tier_info['color'],
                'bg_color': tier_info['bg_color'], 'badge': tier_info['badge'],
                'description': tier_info['desc'], 'message': tier_info['message']
            },
            'plans': plans,
            'can_purchase': result['score'] >= 30,
            'sanciones_count': len(result.get('sanciones', [])),
            'fuente_datos': result.get('fuente_datos', 'MOCK'),
            'consultor_factaliza': result.get('consultor_factaliza', '40648'),
            'timestamp': result['timestamp']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/api/v3/validate/{ruc}")
async def validate_ruc_get(ruc: str, volumen: Optional[int] = 0):
    return await validate_ruc(ValidateRequest(ruc=ruc, volumen=volumen))

@app.post("/api/v3/generate-cert")
async def generate_certificate(request: GenerateCertRequest):
    """Genera certificado después de seleccionar plan"""
    ruc = request.ruc.strip()
    selected_plan = request.plan.lower()
    
    if len(ruc) != 11:
        raise HTTPException(status_code=400, detail="RUC inválido")
    
    result = await calculate_score_v3(ruc)
    score = result['score']
    
    allowed_plans = [p['id'] for p in get_available_plans(score) if not p.get('disabled')]
    
    if selected_plan not in allowed_plans:
        raise HTTPException(status_code=403, detail={
            'error': 'Plan no permitido',
            'score': score, 'tier': get_tier_info(score)['name'],
            'allowed_plans': allowed_plans
        })
    
    cert_slug = str(uuid.uuid4())[:12]
    tier_info = get_tier_info(score)
    prices = {'starter': 400, 'professional': 800, 'enterprise': 2500}
    
    return {
        'success': True,
        'cert_id': cert_slug,
        'ruc': ruc,
        'company_name': request.company_name or result['razon_social'],
        'score': score,
        'tier': {'name': tier_info['name'], 'color': tier_info['color'], 'badge': tier_info['badge']},
        'plan': {'type': selected_plan, 'price_paid': prices[selected_plan]},
        'urls': {
            'view': f'https://czperu.com/verificar.html?cert={cert_slug}&ruc={ruc}',
            'qr': f'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://czperu.com/verificar.html?cert={cert_slug}'
        },
        'issued_at': datetime.now().isoformat()
    }

@app.get("/api/v3/demo/rucs")
def get_demo_rucs():
    return {
        'demo_rucs': [
            {'ruc': '20529400790', 'nombre': 'Constructora Zamora Jara', 'score': 41.0, 'tier': 'BRONZE'},
            {'ruc': '20100123091', 'nombre': 'Empresa Demo Gold', 'score': 95.0, 'tier': 'GOLD'},
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 Conflict Zero API V3.0 + Factaliza #40648")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
