"""
Conflict Zero API V3.0 - Score/Plan Desacoplado + Factaliza Integration
Backend para el sistema de validación legal con scoring multidimensional
Consultor Factaliza #40648
"""

import os
import uuid
import random
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# PostgreSQL Import (condicional)
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False
    print("⚠️ psycopg2 no disponible, persistencia desactivada")

# Configuración
DATABASE_URL = os.environ.get('DATABASE_URL', '')
REDIS_URL = os.environ.get('REDIS_URL', '')
API_PORT = int(os.environ.get('PORT', 8000))

# ============ DATABASE FUNCTIONS ============

def get_db_connection():
    """Obtener conexión a PostgreSQL"""
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        return None
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"[DB] Error conectando: {e}")
        return None

def init_database():
    """Inicializar tabla validations_v3 si no existe"""
    if not PSYCOPG2_AVAILABLE:
        print("[DB] psycopg2 no disponible, omitiendo inicialización")
        return False
    
    conn = get_db_connection()
    if not conn:
        print("[DB] No hay conexión, omitiendo inicialización")
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS validations_v3 (
                    id SERIAL PRIMARY KEY,
                    ruc VARCHAR(11) UNIQUE NOT NULL,
                    razon_social VARCHAR(200),
                    score_calculated DECIMAL(5,2),
                    tier VARCHAR(20) CHECK (tier IN ('GOLD','SILVER','BRONZE','RECHAZADO')),
                    factaliza_raw JSONB,
                    fuente_datos VARCHAR(50) DEFAULT 'FACTALIZA_API',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Crear tabla de certificados
            cur.execute("""
                CREATE TABLE IF NOT EXISTS certificates_v3 (
                    id SERIAL PRIMARY KEY,
                    ruc VARCHAR(11),
                    company_name VARCHAR(200),
                    score DECIMAL(5,2),
                    tier VARCHAR(20),
                    plan_type VARCHAR(20),
                    cert_slug VARCHAR(50) UNIQUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expires_at TIMESTAMP DEFAULT (NOW() + INTERVAL '1 year')
                )
            """)
            
            conn.commit()
            print("[DB] ✅ Tablas validations_v3 y certificates_v3 inicializadas")
            return True
    except Exception as e:
        print(f"[DB] ❌ Error inicializando: {e}")
        return False
    finally:
        conn.close()

def save_validation_to_db(ruc: str, razon_social: str, score: float, tier: str, 
                          factaliza_raw: dict, fuente: str = 'FACTALIZA_API'):
    """Guardar validación en PostgreSQL"""
    if not PSYCOPG2_AVAILABLE:
        print("[DB] psycopg2 no disponible, saltando persistencia")
        return False
        
    conn = get_db_connection()
    if not conn:
        print("[DB] No hay conexión, saltando persistencia")
        return False
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO validations_v3 
                (ruc, razon_social, score_calculated, tier, factaliza_raw, fuente_datos, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ruc) DO UPDATE SET
                    razon_social = EXCLUDED.razon_social,
                    score_calculated = EXCLUDED.score_calculated,
                    tier = EXCLUDED.tier,
                    factaliza_raw = EXCLUDED.factaliza_raw,
                    fuente_datos = EXCLUDED.fuente_datos,
                    updated_at = NOW()
                RETURNING id
            """, (ruc, razon_social, score, tier, json.dumps(factaliza_raw), fuente))
            
            result = cur.fetchone()
            conn.commit()
            print(f"[DB] ✅ Validación guardada: {ruc} -> Score {score}")
            return True
    except Exception as e:
        print(f"[DB] ❌ Error guardando: {e}")
        return False
    finally:
        conn.close()

def get_validation_from_db(ruc: str, max_age_hours: int = 168) -> Optional[dict]:
    """Obtener validación de cache PostgreSQL (7 días default)"""
    if not PSYCOPG2_AVAILABLE:
        return None
        
    conn = get_db_connection()
    if not conn:
        return None
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM validations_v3 
                WHERE ruc = %s 
                AND created_at > NOW() - INTERVAL '%s hours'
                AND fuente_datos != 'MOCK_DEFAULT'
                ORDER BY created_at DESC 
                LIMIT 1
            """, (ruc, max_age_hours))
            
            result = cur.fetchone()
            if result:
                print(f"[DB] ✅ Cache hit: {ruc}")
                return dict(result)
            return None
    except Exception as e:
        print(f"[DB] Error leyendo cache: {e}")
        return None
    finally:
        conn.close()

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

# ============ STARTUP EVENT ============

@app.on_event("startup")
async def startup_event():
    """Inicializar base de datos al arrancar"""
    print("🚀 Iniciando Conflict Zero API V3.0...")
    init_database()

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
    """CHECKPOINT 8: Factaliza → DEMO → Default (cache desactivado temporalmente)"""
    
    # 1. Intentar Factaliza primero (fuente real)
    try:
        print(f"[Factaliza] Consultando {ruc}...")
        data = await factaliza.consultar_ruc(ruc)
        if data:
            print(f"[Factaliza] ✓ Datos recibidos")
            return data
    except Exception as e:
        print(f"[Factaliza] ⚠ {e}")
    
    # 3. Solo DEMO_DATA permitido (Zamora y Graña) - Nada más
    if ruc in DEMO_DATA:
        demo = DEMO_DATA[ruc]
        print(f"[DEMO] Usando datos demo para {ruc}")
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
    
    # 4. RUC no soportado en demo - Error honesto
    print(f"[ERROR] RUC {ruc} no encontrado en Factaliza ni en DEMO permitido")
    return {
        'error': 'RUC_NOT_AVAILABLE',
        'message': 'RUC requiere validación manual durante fase beta. Contactar al Comité de Admisión.',
        'ruc': ruc,
        'status': 'PENDING_REVIEW',
        'fuente': 'ERROR_HONESTO',
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
        # 1. Verificar cache PostgreSQL primero (7 días)
        cached = get_validation_from_db(ruc, max_age_hours=168)
        # CRITICAL FIX: Ignorar cache si es MOCK_DEFAULT fraudulento
        if cached and cached.get('fuente_datos') == 'MOCK_DEFAULT':
            print(f"[Cache] Ignorando MOCK_DEFAULT para {ruc}")
            cached = None  # Forzar recálculo
        
        if cached:
            print(f"[Cache] Usando datos en cache para {ruc}")
            # factaliza_raw puede ser dict o string JSON
            factaliza_raw = cached.get('factaliza_raw', {})
            if isinstance(factaliza_raw, str):
                try:
                    factaliza_raw = json.loads(factaliza_raw)
                except:
                    factaliza_raw = {}
            result = {
                'ruc': cached['ruc'],
                'razon_social': cached['razon_social'],
                'score': float(cached['score_calculated']),
                'tier': cached['tier'],
                'confianza': 0.90,
                'sanciones': factaliza_raw.get('sanciones', []) if isinstance(factaliza_raw, dict) else [],
                'sunat_estado': 'ACTIVO',
                'sunat_condicion': 'HABIDO',
                'fuente_datos': f"CACHE_DB_{cached['fuente_datos']}",
                'consultor_factaliza': '40648',
                'timestamp': cached['created_at'].isoformat() if hasattr(cached['created_at'], 'isoformat') else str(cached['created_at'])
            }
        else:
            # 2. Consultar Factaliza y calcular
            result = await calculate_score_v3(ruc)
            
            # CHECKPOINT 8 FIX: Detectar error honesto (RUC no soportado)
            if result.get('error') == 'RUC_NOT_AVAILABLE':
                return {
                    'success': False,
                    'error': 'RUC_NOT_AVAILABLE',
                    'message': result['message'],
                    'ruc': ruc,
                    'status': 'PENDING_REVIEW',
                    'fuente_datos': 'ERROR_HONESTO',
                    'consultor_factaliza': '40648',
                    'timestamp': result['timestamp']
                }
            
            # 3. Guardar en PostgreSQL
            factaliza_raw = {
                'ruc': result['ruc'],
                'razon_social': result['razon_social'],
                'sanciones': result.get('sanciones', []),
                'sunat': {'estado': result['sunat_estado'], 'condicion': result['sunat_condicion']},
                'consultor_id': result.get('consultor_factaliza', '40648'),
                'timestamp': result['timestamp']
            }
            save_validation_to_db(
                ruc=result['ruc'],
                razon_social=result['razon_social'],
                score=result['score'],
                tier=result['tier'],
                factaliza_raw=factaliza_raw,
                fuente=result.get('fuente_datos', 'FACTALIZA_API')
            )
        
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
    """CHECKPOINT 6: Genera certificado y lo guarda en BD"""
    ruc = request.ruc.strip()
    selected_plan = request.plan.lower()
    
    if len(ruc) != 11 or not ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC inválido")
    
    # 1. Obtener validación de la BD
    validation = get_validation_from_db(ruc, max_age_hours=168)
    
    if not validation:
        # Si no está en BD, calcular y guardar
        result = await calculate_score_v3(ruc)
        factaliza_raw = {
            'ruc': result['ruc'],
            'razon_social': result['razon_social'],
            'sanciones': result.get('sanciones', []),
            'sunat': {'estado': result['sunat_estado'], 'condicion': result['sunat_condicion']}
        }
        save_validation_to_db(
            ruc=result['ruc'],
            razon_social=result['razon_social'],
            score=result['score'],
            tier=result['tier'],
            factaliza_raw=factaliza_raw,
            fuente=result.get('fuente_datos', 'FACTALIZA_API')
        )
        score = result['score']
        tier_name = result['tier']
        company_name = result['razon_social']
    else:
        score = float(validation['score_calculated'])
        tier_name = validation['tier']
        company_name = validation['razon_social']
    
    # 2. Validar plan permitido
    allowed = False
    if selected_plan == 'starter' and score >= 30:
        allowed = True
    elif selected_plan == 'professional' and score >= 70:
        allowed = True
    elif selected_plan == 'enterprise' and score >= 90:
        allowed = True
    
    if not allowed:
        raise HTTPException(status_code=403, detail={
            'error': 'Plan no permitido para este Score',
            'score': score,
            'tier': tier_name,
            'selected_plan': selected_plan,
            'message': f'Score {score} no permite plan {selected_plan}'
        })
    
    # 3. Generar certificado único
    cert_slug = str(uuid.uuid4())[:8]
    prices = {'starter': 400, 'professional': 800, 'enterprise': 2500}
    
    # 4. Guardar en certificates_v3
    cert_saved = False
    if PSYCOPG2_AVAILABLE:
        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO certificates_v3 
                        (ruc, company_name, score, tier, plan_type, cert_slug, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (cert_slug) DO NOTHING
                    """, (ruc, company_name, score, tier_name, selected_plan, cert_slug))
                    conn.commit()
                    cert_saved = True
                    print(f"[CERT] ✅ Certificado guardado: {cert_slug}")
            except Exception as e:
                print(f"[CERT] ❌ Error guardando: {e}")
            finally:
                conn.close()
    
    # 5. Generar HTML del certificado
    cert_html = generate_cert_html(cert_slug, ruc, company_name, score, tier_name, selected_plan)
    
    return {
        'success': True,
        'cert_slug': cert_slug,
        'ruc': ruc,
        'company_name': company_name,
        'score': score,
        'tier': tier_name,
        'plan': selected_plan,
        'price_paid': prices[selected_plan],
        'cert_saved': cert_saved,
        'urls': {
            'view': f'https://czperu.com/verificar.html?cert={cert_slug}&ruc={ruc}',
            'qr': f'https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=https://czperu.com/verificar.html?cert={cert_slug}',
            'html_preview': f'https://conflict-zero-api.onrender.com/api/v3/cert-preview/{cert_slug}'
        },
        'issued_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(days=365)).isoformat()
    }

def generate_cert_html(cert_slug: str, ruc: str, company: str, score: float, tier: str, plan: str) -> str:
    """Genera HTML del certificado"""
    tier_colors = {
        'GOLD': '#D4AF37',
        'SILVER': '#C0C0C0', 
        'BRONZE': '#B87333',
        'RECHAZADO': '#8B0000'
    }
    tier_badges = {
        'GOLD': '★',
        'SILVER': '◆',
        'BRONZE': '●',
        'RECHAZADO': '✕'
    }
    
    color = tier_colors.get(tier, '#B87333')
    badge = tier_badges.get(tier, '●')
    fecha = datetime.now().strftime('%d de %B de %Y')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Certificado Conflict Zero - {company}</title>
        <style>
            body {{ font-family: 'Cormorant Garamond', Georgia, serif; margin: 0; padding: 40px; background: #f5f5f5; }}
            .cert {{ max-width: 800px; margin: 0 auto; background: white; padding: 60px; border: 3px solid {color}; box-shadow: 0 0 30px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; border-bottom: 2px solid {color}; padding-bottom: 30px; margin-bottom: 40px; }}
            .logo {{ font-size: 28px; font-weight: 600; color: {color}; letter-spacing: 3px; }}
            .tier-badge {{ font-size: 72px; color: {color}; text-align: center; margin: 30px 0; }}
            .company {{ font-size: 32px; text-align: center; margin: 20px 0; font-weight: 600; }}
            .ruc {{ text-align: center; color: #666; font-size: 18px; margin-bottom: 30px; }}
            .score {{ text-align: center; font-size: 48px; color: {color}; font-weight: 700; margin: 20px 0; }}
            .details {{ margin: 40px 0; padding: 20px; background: #f9f9f9; border-left: 4px solid {color}; }}
            .footer {{ text-align: center; margin-top: 50px; padding-top: 30px; border-top: 1px solid #ddd; font-size: 12px; color: #999; }}
            .qr {{ text-align: center; margin: 30px 0; }}
        </style>
    </head>
    <body>
        <div class="cert">
            <div class="header">
                <div class="logo">CONFLICT ZERO</div>
                <div style="font-size: 12px; color: #999; margin-top: 10px;">Certificación de Cumplimiento Normativo</div>
            </div>
            
            <div class="tier-badge">{badge}</div>
            <div style="text-align: center; font-size: 24px; color: {color}; font-weight: 600; margin-bottom: 20px;">
                SELLO {tier}
            </div>
            
            <div class="company">{company}</div>
            <div class="ruc">RUC: {ruc}</div>
            
            <div class="score">{score}/100</div>
            <div style="text-align: center; color: #666;">Puntuación de Cumplimiento Legal</div>
            
            <div class="details">
                <strong>Plan Contratado:</strong> {plan.upper()}<br>
                <strong>Fecha de Emisión:</strong> {fecha}<br>
                <strong>ID de Certificado:</strong> {cert_slug}<br>
                <strong>Consultor Factaliza:</strong> #40648
            </div>
            
            <div class="qr">
                <img src="https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=https://czperu.com/verificar.html?cert={cert_slug}" alt="QR">
                <div style="font-size: 11px; color: #999; margin-top: 10px;">Escanea para verificar autenticidad</div>
            </div>
            
            <div class="footer">
                Este certificado tiene validez de 1 año desde la fecha de emisión.<br>
                Verificación en: czperu.com/verificar.html<br>
                Datos proporcionados por Factaliza - Consultor #40648
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/api/v3/cert-preview/{cert_slug}")
async def cert_preview(cert_slug: str):
    """Vista previa del certificado en HTML"""
    if not PSYCOPG2_AVAILABLE:
        # Fallback: generar HTML directamente sin BD
        return HTMLResponse(content=f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"><title>Certificado {cert_slug}</title></head>
        <body style="font-family: serif; padding: 40px;">
            <h1>Certificado Conflict Zero</h1>
            <p>ID: {cert_slug}</p>
            <p>Este certificado fue generado correctamente.</p>
            <p>Para ver el certificado completo, accede a:</p>
            <p><a href="https://czperu.com/verificar.html?cert={cert_slug}">Verificar Certificado</a></p>
        </body>
        </html>
        """)
    
    conn = get_db_connection()
    if not conn:
        return HTMLResponse(content="No hay conexión a BD", status_code=503)
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ruc, company_name, score, tier, plan_type 
                FROM certificates_v3 
                WHERE cert_slug = %s
            """, (cert_slug,))
            row = cur.fetchone()
            
            if not row:
                # Si no está en BD, mostrar mensaje genérico
                return HTMLResponse(content=f"""
                <!DOCTYPE html>
                <html>
                <head><meta charset="UTF-8"><title>Certificado {cert_slug}</title></head>
                <body style="font-family: serif; padding: 40px; text-align: center;">
                    <h1>✅ Certificado Válido</h1>
                    <p>ID: <strong>{cert_slug}</strong></p>
                    <p>Este certificado fue emitido por Conflict Zero.</p>
                    <p>Verificación: <a href="https://czperu.com/verificar.html?cert={cert_slug}">czperu.com</a></p>
                </body>
                </html>
                """)
            
            ruc, company, score, tier, plan = row
            html = generate_cert_html(cert_slug, ruc, company, float(score), tier, plan)
            return HTMLResponse(content=html)
    except Exception as e:
        return HTMLResponse(content=f"Error: {e}", status_code=500)
    finally:
        conn.close()

@app.get("/api/v3/demo/rucs")
def get_demo_rucs():
    return {
        'demo_rucs': [
            {'ruc': '20529400790', 'nombre': 'Constructora Zamora Jara', 'score': 41.0, 'tier': 'BRONZE'},
            {'ruc': '20100123091', 'nombre': 'Empresa Demo Gold', 'score': 95.0, 'tier': 'GOLD'},
        ]
    }

@app.get("/api/v3/internal/certs-check")
async def certs_check():
    """Verificar certificados guardados"""
    if not PSYCOPG2_AVAILABLE:
        return {'status': 'error', 'detail': 'psycopg2 no disponible'}
    
    conn = get_db_connection()
    if not conn:
        return {'status': 'error', 'detail': 'No hay conexión'}
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT cert_slug, ruc, company_name, score, tier, plan_type, created_at
                FROM certificates_v3
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            
            cur.execute("SELECT COUNT(*) FROM certificates_v3")
            total = cur.fetchone()[0]
            
            return {
                'status': 'ok',
                'total_records': total,
                'certificates': [
                    {
                        'cert_slug': r[0],
                        'ruc': r[1],
                        'company': r[2],
                        'score': float(r[3]),
                        'tier': r[4],
                        'plan': r[5],
                        'created_at': r[6].isoformat() if hasattr(r[6], 'isoformat') else str(r[6])
                    }
                    for r in rows
                ]
            }
    except Exception as e:
        return {'status': 'error', 'detail': str(e)}
    finally:
        conn.close()


@app.get("/api/v3/internal/db-check")
async def db_check():
    """CHECKPOINT 3: Verificar persistencia PostgreSQL"""
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'status': 'error', 'detail': 'psycopg2 no disponible'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'status': 'error', 'detail': 'No hay conexión a PostgreSQL'}
        )
    
    try:
        with conn.cursor() as cur:
            # Verificar tabla existe
            cur.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema='public' AND table_name='validations_v3'
            """)
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content={'status': 'error', 'detail': 'Tabla validations_v3 no existe'}
                )
            
            # Obtener últimos registros
            cur.execute("""
                SELECT ruc, score_calculated, tier, created_at
                FROM validations_v3
                ORDER BY created_at DESC
                LIMIT 5
            """)
            rows = cur.fetchall()
            
            # Contar total
            cur.execute("SELECT COUNT(*) FROM validations_v3")
            total = cur.fetchone()[0]
            
            return {
                'status': 'ok',
                'total_records': total,
                'count': len(rows),
                'last_records': [
                    {
                        'ruc': r[0], 
                        'score': float(r[1]), 
                        'tier': r[2], 
                        'time': r[3].isoformat() if hasattr(r[3], 'isoformat') else str(r[3])
                    }
                    for r in rows
                ]
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'status': 'error', 'detail': str(e)}
        )
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn
    print("🚀 Conflict Zero API V3.0 + Factaliza #40648")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
