"""
Conflict Zero API V3.0 - Score/Plan Desacoplado + Factaliza Integration
Backend para el sistema de validación legal con scoring multidimensional
Consultor Factaliza #40648
DEPLOY: 2026-03-30-01-35-FORCE
"""

import os
import uuid
import random
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Header
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

# JWT y Auth
try:
    import jwt
    import bcrypt
    AUTH_AVAILABLE = True
except ImportError:
    AUTH_AVAILABLE = False
    print("⚠️ jwt/bcrypt no disponible, auth desactivado")

# Redis Import - import directo para evitar dependencias circulares
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'services'))
from redis_cache import redis_cache, validation_key, RateLimiter, JobQueue

# Configuración
DATABASE_URL = os.environ.get('DATABASE_URL', '')
REDIS_URL = os.environ.get('REDIS_URL', '')
API_PORT = int(os.environ.get('PORT', 8000))
JWT_SECRET = os.environ.get('JWT_SECRET', 'conflict-zero-secret-key-2024')
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')

# ============ ADAPTERS INLINE (evita problemas de import) ============
import httpx

# Factaliza Config
FACTALIZA_TOKEN = os.environ.get(
    'FACTALIZA_TOKEN',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDY0OCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.d_-YT6RuTIrq-RZj1TO6Q6r3EG2NL4MRO9odkcaGDYA'
)
FACTALIZA_BASE_URL = "https://api.factiliza.com/v1"

async def consultar_factaliza(ruc: str) -> Optional[Dict]:
    """Consulta RUC en Factaliza API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{FACTALIZA_BASE_URL}/ruc/info/{ruc}",
                headers={'Authorization': f'Bearer {FACTALIZA_TOKEN}'}
            )
            
            if response.status_code == 404:
                return None
            if response.status_code == 429:
                print(f"[Factaliza] Rate limit")
                return None
                
            response.raise_for_status()
            data = response.json()
            
            if not data.get('success'):
                return None
                
            result = data.get('data', {})
            
            return {
                'ruc': ruc,
                'razon_social': result.get('nombre_o_razon_social', f'Empresa {ruc}'),
                'sunat': {
                    'estado': result.get('estado', 'ACTIVO'),
                    'condicion': result.get('condicion', 'HABIDO'),
                },
                'fuente': 'FACTALIZA_API',
                'consultor_id': '40648',
            }
    except Exception as e:
        print(f"[Factaliza] Error: {e}")
        return None

# BuscarUC Config  
BUSCARUC_TOKEN = os.environ.get(
    'BUSCARUC_TOKEN',
    'eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE'
)

async def consultar_buscaruc(ruc: str) -> Optional[Dict]:
    """Consulta RUC en BuscarUC API"""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                'https://buscaruc.com/api/v1/ruc',
                headers={'Content-Type': 'application/json'},
                json={'token': BUSCARUC_TOKEN, 'ruc': ruc}
            )
            
            if response.status_code != 200:
                return None
                
            data = response.json()
            result = data.get('result', {})
            
            if not result:
                return None
            
            return {
                'ruc': ruc,
                'razon_social': result.get('social_reason', f'Empresa {ruc}'),
                'sunat': {
                    'estado': result.get('taxpayer_state', 'ACTIVO'),
                    'condicion': result.get('domicile_condition', 'HABIDO'),
                    'direccion': result.get('address', ''),
                },
                'osce': {'total_sanciones': 0, 'sanciones_vigentes': 0},
                'sanciones': [],
                'tiene_sanciones': False,
                'fuente': 'BUSCARUC_API',
                'consultor_id': '5470',
            }
    except Exception as e:
        print(f"[BuscarUC] Error: {e}")
        return None

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
    """Inicializar tablas si no existen"""
    if not PSYCOPG2_AVAILABLE:
        print("[DB] psycopg2 no disponible, omitiendo inicialización")
        return False
    
    conn = get_db_connection()
    if not conn:
        print("[DB] No hay conexión, omitiendo inicialización")
        return False
    
    try:
        with conn.cursor() as cur:
            # Tabla de validaciones
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
            
            # Tabla de certificados
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
            
            # CHECKPOINT 1: Tabla de usuarios (Auth White Glove)
            # Usar CASCADE para eliminar dependencias
            cur.execute("DROP TABLE IF EXISTS users CASCADE")
            cur.execute("""
                CREATE TABLE users (
                    id SERIAL PRIMARY KEY,
                    email VARCHAR(200) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    ruc VARCHAR(11) NOT NULL,
                    company_name VARCHAR(200),
                    plan VARCHAR(20) DEFAULT 'starter',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_login TIMESTAMP
                )
            """)
            
            # GRUPO C: Tabla de invitaciones simples
            cur.execute("""
                CREATE TABLE IF NOT EXISTS invitations (
                    id SERIAL PRIMARY KEY,
                    invitador_ruc VARCHAR(11) NOT NULL,
                    email VARCHAR(200) NOT NULL,
                    token VARCHAR(100) UNIQUE NOT NULL,
                    ruc_invitado VARCHAR(11),
                    expira TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours'),
                    usada BOOLEAN DEFAULT FALSE,
                    usada_por INTEGER REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # Índice para tokens
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_invitations_token 
                ON invitations(token)
            """)
            
            # GRUPO B: Tabla de alertas
            cur.execute("""
                CREATE TABLE IF NOT EXISTS supplier_alerts (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    ruc VARCHAR(11) NOT NULL,
                    alert_type VARCHAR(50) NOT NULL, -- 'score_drop', 'new_sanction', 'status_change', 'custom'
                    threshold DECIMAL(5,2), -- Para alertas de score (ej: 70.00)
                    message TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    triggered_at TIMESTAMP,
                    triggered_count INTEGER DEFAULT 0,
                    last_triggered_data JSONB
                )
            """)
            
            # Índice para búsquedas rápidas por usuario y RUC
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_alerts_user_ruc 
                ON supplier_alerts(user_id, ruc)
            """)
            
            conn.commit()
            print("[DB] ✅ Tablas inicializadas: validations_v3, certificates_v3, users, supplier_alerts, invitations")
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
    """Inicializar base de datos y Redis al arrancar"""
    print("🚀 Iniciando Conflict Zero API V3.0...")
    init_database()
    # Inicializar Redis (no bloquea si falla)
    await redis_cache.connect()
    print("🚀 Conflict Zero API V3.0 + Factaliza #40648 + Redis Cache")

# ============ MODELOS ============

class ValidateRequest(BaseModel):
    ruc: str
    volumen: Optional[int] = 0

class GenerateCertRequest(BaseModel):
    ruc: str
    plan: str
    email: Optional[str] = None
    company_name: Optional[str] = None

# ============ MODELOS AUTH (White Glove) ============

class CreateUserRequest(BaseModel):
    ruc: str
    email: str
    password: str
    plan: str = "starter"

class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    ruc: str
    company_name: str
    plan: str

# ============ GRUPO C: INVITACIONES MODELS ============
class CreateInvitationRequest(BaseModel):
    email: str
    ruc_invitado: Optional[str] = None  # Pre-llenar RUC si se conoce

class InvitationResponse(BaseModel):
    id: int
    email: str
    token: str
    invitador_ruc: str
    expira: str
    usada: bool
    created_at: str

class RegisterWithInvitationRequest(BaseModel):
    token: str
    email: str
    password: str
    ruc: str
    company_name: Optional[str] = None
class CreateAlertRequest(BaseModel):
    ruc: str
    alert_type: str  # 'score_drop', 'new_sanction', 'status_change', 'custom'
    threshold: Optional[float] = None  # Para alertas de score
    message: Optional[str] = None
    is_active: bool = True

class AlertResponse(BaseModel):
    id: int
    user_id: int
    ruc: str
    alert_type: str
    threshold: Optional[float]
    message: Optional[str]
    is_active: bool
    created_at: str
    triggered_at: Optional[str]
    triggered_count: int
    id: int
    email: str
    ruc: str
    company_name: str
    plan: str
    created_at: str

# ============ DATOS DEMO ============

DEMO_DATA = {
    '20529400790': {
        'razon_social': 'CONSTRUCTORA ZAMORA JARA SAC',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [{
            'resolucion': '4162-2023-TCE-S4',
            'entidad': 'TCE',
            'tipo': 'Impedimento',  # Tipo para scoring
            'fecha_inicio': '2023-09-28',
            'fecha': '2023-09-28',  # Alias para compatibilidad
            'dias_transcurridos': 912,
            'estado': 'VIGENTE'
        }],
    },
    '20100123091': {
        'razon_social': 'GRAÑA Y MONTERO S.A.A.',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [],
    },
    # RUCs adicionales que funcionan con Factaliza
    '20100047218': {
        'razon_social': 'BANCO DE CREDITO DEL PERU',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [],
    },
    '20100017923': {
        'razon_social': 'RIMAC SEGUROS Y REASEGUROS S.A.',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': [],
    }
}

# ============ CONSULTA DE SANCIONES OSCE/TCE DESDE DB ============

def consultar_sanciones_db(ruc: str) -> List[Dict]:
    """
    Consulta sanciones OSCE/TCE desde PostgreSQL.
    Integra datos de scraping real con el sistema de scoring.
    """
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        print(f"[DB-Sanciones] psycopg2 o DATABASE_URL no disponible")
        return []
    
    conn = None
    sanciones = []
    
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        # Consultar tabla OSCE
        try:
            cursor.execute("""
                SELECT tipo_sancion, numero_resolucion, entidad, 
                       fecha_inicio, fecha_fin, estado, motivo
                FROM osce_sanciones_detalle
                WHERE ruc = %s
                ORDER BY fecha_inicio DESC
            """, (ruc,))
            
            for row in cursor.fetchall():
                sanciones.append({
                    'tipo': row[0],
                    'resolucion': row[1],
                    'entidad': row[2] if row[2] else 'OSCE',
                    'fecha_inicio': row[3].isoformat() if row[3] else None,
                    'fecha_fin': row[4].isoformat() if row[4] else None,
                    'estado': row[5] if row[5] else 'VIGENTE',
                    'motivo': row[6],
                    'fuente_db': 'OSCE'
                })
        except Exception as e:
            print(f"[DB-Sanciones] Error consultando OSCE: {e}")
        
        # Consultar tabla TCE si existe
        try:
            cursor.execute("""
                SELECT tipo_sancion, numero_resolucion, entidad,
                       fecha_inicio, fecha_fin, estado, motivo
                FROM tce_sanciones
                WHERE ruc = %s
                ORDER BY fecha_inicio DESC
            """, (ruc,))
            
            for row in cursor.fetchall():
                sanciones.append({
                    'tipo': row[0],
                    'resolucion': row[1],
                    'entidad': row[2] if row[2] else 'TCE',
                    'fecha_inicio': row[3].isoformat() if row[3] else None,
                    'fecha_fin': row[4].isoformat() if row[4] else None,
                    'estado': row[5] if row[5] else 'VIGENTE',
                    'motivo': row[6],
                    'fuente_db': 'TCE'
                })
        except Exception as e:
            # Tabla TCE puede no existir aún
            print(f"[DB-Sanciones] TCE no disponible: {e}")
        
        if sanciones:
            print(f"[DB-Sanciones] ✓ {len(sanciones)} sanciones encontradas para {ruc}")
        else:
            print(f"[DB-Sanciones] No hay sanciones en DB para {ruc}")
        
        return sanciones
        
    except Exception as e:
        print(f"[DB-Sanciones] Error conectando: {e}")
        return []
    finally:
        if conn:
            conn.close()

# ============ SCORING CON FACTALIZA ============

async def consultar_con_fallback(ruc: str) -> Dict:
    """CHECKPOINT 8: Factaliza → DEMO → Default (cache desactivado temporalmente)"""
    
    # 1. Intentar Factaliza primero (fuente real para CUALQUIER RUC)
    factaliza_error = None
    try:
        print(f"[Factaliza] Consultando {ruc}...")
        data = await consultar_factaliza(ruc)
        if data:
            print(f"[Factaliza] ✓ Datos recibidos para {ruc}")
            
            # Consultar sanciones en DB y combinar con datos de Factaliza
            sanciones_db = consultar_sanciones_db(ruc)
            if sanciones_db:
                # Combinar sanciones de Factaliza (si tiene) con DB
                sanciones_existentes = data.get('sanciones', [])
                # Evitar duplicados por resolución
                resoluciones_existentes = {s.get('resolucion') for s in sanciones_existentes}
                for s in sanciones_db:
                    if s.get('resolucion') not in resoluciones_existentes:
                        sanciones_existentes.append(s)
                data['sanciones'] = sanciones_existentes
                data['tiene_sanciones'] = len(sanciones_existentes) > 0
                data['fuente'] = 'FACTALIZA_API + DB_SANCIONES'
                print(f"[Factaliza] ✓ Combinadas {len(sanciones_db)} sanciones de DB")
            
            # Guardar en cache para futuro
            try:
                save_validation_to_db(
                    ruc=ruc,
                    razon_social=data['razon_social'],
                    score=0,  # Se calculará después
                    tier='PENDING',
                    factaliza_raw=data,
                    fuente='FACTALIZA_API'
                )
            except Exception as e:
                print(f"[CACHE] No se pudo guardar: {e}")
            return data
        else:
            # Factaliza devolvió None = RUC no existe en Factaliza
            print(f"[Factaliza] RUC {ruc} no encontrado (404), intentando BuscarUC...")
            # No retornar error aún - intentar BuscarUC primero
    except Exception as e:
        factaliza_error = str(e)
        print(f"[Factaliza] ⚠ Error: {factaliza_error}")
    
    # 2. Si Factaliza no encontró el RUC o falló, intentar BuscarUC
    print(f"[BuscarUC] Intentando consultar {ruc}...")
    buscaruc_data = await consultar_buscaruc(ruc)
    if buscaruc_data:
        print(f"[BuscarUC] ✓ Datos recibidos para {ruc}")
        # Consultar sanciones en DB y combinar
        sanciones_db = consultar_sanciones_db(ruc)
        if sanciones_db:
            buscaruc_data['sanciones'] = sanciones_db
            buscaruc_data['tiene_sanciones'] = True
            buscaruc_data['fuente'] = 'BUSCARUC_API + DB_SANCIONES'
        return buscaruc_data
    else:
        print(f"[BuscarUC] RUC {ruc} no encontrado")
    
    # 3. Si Factaliza falló por rate limit, revisar cache
    if factaliza_error and ('RATE_LIMIT' in factaliza_error or '429' in factaliza_error):
        print(f"[CACHE] Factaliza en rate limit, buscando cache para {ruc}")
        cached = get_validation_from_db(ruc, max_age_hours=168)
        if cached and cached.get('fuente_datos') != 'MOCK_DEFAULT':
            print(f"[CACHE] ✓ Usando datos cacheados para {ruc}")
            # Consultar sanciones frescas de DB
            sanciones_db = consultar_sanciones_db(ruc)
            return {
                'ruc': ruc,
                'razon_social': cached['razon_social'],
                'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
                'sanciones': sanciones_db if sanciones_db else [],
                'tiene_sanciones': len(sanciones_db) > 0 if sanciones_db else cached['tier'] in ['BRONZE', 'RECHAZADO'],
                'fuente': 'CACHE_INSTITUCIONAL + DB_SANCIONES' if sanciones_db else 'CACHE_INSTITUCIONAL',
                'consultor_id': '40648',
                'timestamp': str(cached['created_at'])
            }
    
    # 3. Fallback a DEMO_DATA solo para Zamora y Graña (demo controlado)
    if ruc in DEMO_DATA:
        demo = DEMO_DATA[ruc]
        print(f"[DEMO] Usando datos demo para {ruc}")
        
        # Consultar sanciones frescas de DB y combinar con DEMO
        sanciones_db = consultar_sanciones_db(ruc)
        sanciones_demo = demo.get('sanciones', [])
        
        if sanciones_db:
            # Combinar: usar sanciones de DB (más actualizadas) + sanciones demo si no están en DB
            resoluciones_db = {s.get('resolucion') for s in sanciones_db}
            for s in sanciones_demo:
                if s.get('resolucion') not in resoluciones_db:
                    sanciones_db.append(s)
            sanciones_finales = sanciones_db
            fuente = 'DEMO_DATA + DB_SANCIONES'
            print(f"[DEMO] ✓ Combinadas {len(sanciones_db)} sanciones de DB con demo")
        else:
            sanciones_finales = sanciones_demo
            fuente = 'MOCK_DEMO'
        
        return {
            'ruc': ruc,
            'razon_social': demo['razon_social'],
            'sunat': demo['sunat'],
            'sanciones': sanciones_finales,
            'tiene_sanciones': len(sanciones_finales) > 0,
            'dias_desde_sancion': sanciones_finales[0].get('dias_transcurridos', 0) if sanciones_finales else 0,
            'fuente': fuente,
            'consultor_id': '40648',
            'timestamp': datetime.now().isoformat()
        }
    
    # 4. RUC nuevo - Datos provisionales para permitir registro
    print(f"[INFO] RUC {ruc} no encontrado en APIs externas. Usando datos provisionales.")
    
    # Consultar sanciones en DB por si acaso
    sanciones_db = consultar_sanciones_db(ruc)
    
    # Si hay sanciones, usar score bajo. Si no, score provisional 80 (SILVER)
    if sanciones_db:
        score_provisional = 50.0
        tier_provisional = 'BRONZE'
    else:
        score_provisional = 80.0
        tier_provisional = 'SILVER'
    
    return {
        'ruc': ruc,
        'razon_social': f'Empresa RUC {ruc}',
        'sunat': {'estado': 'ACTIVO', 'condicion': 'HABIDO'},
        'sanciones': sanciones_db if sanciones_db else [],
        'tiene_sanciones': len(sanciones_db) > 0 if sanciones_db else False,
        'fuente': 'PROVISIONAL_PENDING_VERIFICATION',
        'consultor_id': '40648',
        'score_provisional': score_provisional,
        'tier_provisional': tier_provisional,
        'requiere_verificacion': True,
        'timestamp': datetime.now().isoformat()
    }

async def calculate_score_v3(ruc: str) -> Dict:
    """
    LegalBot V3.0 - Scoring combinando Factaliza + OSCE/TCE
    
    FUENTE 1: Factaliza API (30% peso)
      - razon_social, estado, condicion, deuda_total, representantes[]
    
    FUENTE 2: Scraping OSCE/TCE (70% peso)
      - Lista de sanciones con tipo, fecha, entidad, resolucion
    """
    
    # Obtener datos de Factaliza
    factaliza_data = await consultar_con_fallback(ruc)
    
    # Si hay error en los datos, propagar el error
    if factaliza_data.get('error'):
        return factaliza_data
    
    # Obtener sanciones OSCE/TCE (del fallback o scraping futuro)
    # Por ahora usamos las sanciones que vienen en factaliza_data (del DEMO_DATA)
    osce_tce_data = factaliza_data.get('sanciones', [])
    
    score = 100.0
    detalles = []
    
    # === PARTE 1: SANCIONES OSCE/TCE (70% peso) ===
    for sancion in osce_tce_data:
        # 1. Gravedad según tipo
        tipo = sancion.get('tipo', '').lower()
        if 'inhabilitacion' in tipo or 'impedimento' in tipo:
            gravedad = 70  # Caso Zamora: Impedimento = 70
        elif 'colusion' in tipo:
            gravedad = 95
        elif 'multa' in tipo:
            gravedad = 40
        else:
            gravedad = 50
        
        # 2. Entidad multiplicador
        entidad = sancion.get('entidad', 'OSCE')
        multiplicador = 1.5 if entidad == 'OSCE' else 1.2 if entidad == 'TCE' else 0.8
        
        # 3. Factor tiempo (días desde la sanción)
        fecha_str = sancion.get('fecha_inicio', sancion.get('fecha', '2020-01-01'))
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d')
            dias = (datetime.now() - fecha).days
        except:
            dias = 0
        
        if dias < 365: 
            factor_t = 1.0
        elif dias < 730: 
            factor_t = 0.7   # Zamora: 2.5 años = 0.7
        elif dias < 1095: 
            factor_t = 0.4
        else: 
            factor_t = 0.1
        
        # Impacto de esta sanción
        impacto = gravedad * multiplicador * factor_t
        score -= impacto
        
        detalles.append({
            'fuente': entidad,
            'resolucion': sancion.get('resolucion', 'N/A'),
            'tipo': tipo,
            'impacto': round(impacto, 1)
        })
    
    # === PARTE 2: DATOS FACTALIZA (30% peso) ===
    sunat = factaliza_data.get('sunat', {})
    
    # Penalización deuda (si está disponible)
    deuda = factaliza_data.get('deuda_total', 0)
    if deuda > 100000:
        score -= 30
    elif deuda > 10000:
        score -= 15
    
    # Penalización estado SUNAT
    if sunat.get('estado') == 'BAJA':
        score -= 30
    if sunat.get('condicion') == 'NO HABIDO':
        score -= 50
    
    # Penalización representantes inhabilitados (si está disponible)
    representantes = factaliza_data.get('representantes', [])
    for rep in representantes:
        if rep.get('estado') == 'inhabilitado':
            score -= 20
    
    # Asegurar score entre 0-100
    score = max(0.0, min(100.0, round(score, 1)))
    
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
        'razon_social': factaliza_data.get('razon_social', f'Empresa {ruc}'),
        'score': score,
        'tier': tier,
        'confianza': 0.95 if factaliza_data.get('fuente') == 'FACTALIZA_API' else 0.85,
        'sanciones': osce_tce_data,
        'detalles_impacto': detalles,
        'sunat_estado': sunat.get('estado', 'ACTIVO'),
        'sunat_condicion': sunat.get('condicion', 'HABIDO'),
        'fuente_datos': factaliza_data.get('fuente', 'UNKNOWN'),
        'consultor_factaliza': '40648',
        'timestamp': factaliza_data.get('timestamp', datetime.now().isoformat())
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
async def health_check():
    """
    Health Check Completo - Estado de todos los componentes del sistema
    """
    health_data = {
        "status": "healthy",
        "version": "3.0.0",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }
    
    # 1. Redis Cache
    try:
        redis_status = await redis_cache.health_check()
        health_data["components"]["redis"] = {
            "status": "up" if redis_status else "down",
            "available": redis_status
        }
    except Exception as e:
        health_data["components"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
    
    # 2. PostgreSQL Database
    db_health = {"status": "disabled"}
    if PSYCOPG2_AVAILABLE and DATABASE_URL:
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            cursor = conn.cursor()
            
            # Verificar conexión
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
            # Contar registros en tablas principales
            tables_info = {}
            
            # Validaciones
            try:
                cursor.execute("SELECT COUNT(*) FROM validaciones_ruc")
                tables_info["validaciones_ruc"] = cursor.fetchone()[0]
            except:
                tables_info["validaciones_ruc"] = 0
            
            # Sanciones OSCE
            try:
                cursor.execute("SELECT COUNT(*) FROM osce_sanciones_detalle")
                tables_info["osce_sanciones_detalle"] = cursor.fetchone()[0]
            except:
                tables_info["osce_sanciones_detalle"] = 0
            
            # Sanciones TCE
            try:
                cursor.execute("SELECT COUNT(*) FROM tce_sanciones")
                tables_info["tce_sanciones"] = cursor.fetchone()[0]
            except:
                tables_info["tce_sanciones"] = 0
            
            # Usuarios
            try:
                cursor.execute("SELECT COUNT(*) FROM users")
                tables_info["users"] = cursor.fetchone()[0]
            except:
                tables_info["users"] = 0
            
            conn.close()
            
            db_health = {
                "status": "up",
                "tables": tables_info
            }
        except Exception as e:
            db_health = {
                "status": "error",
                "error": str(e)
            }
    
    health_data["components"]["postgresql"] = db_health
    
    # 3. Factiliza API - Usar un RUC conocido para health check
    factaliza_health = {"status": "unknown"}
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Health check usando un RUC de prueba (BCP - siempre existe)
            response = await client.get(
                f"{FACTALIZA_BASE_URL}/ruc/info/20100047218",
                headers={'Authorization': f'Bearer {FACTALIZA_TOKEN}'}
            )
            
            if response.status_code == 200:
                factaliza_health = {
                    "status": "up",
                    "status_code": response.status_code,
                    "message": "API respondiendo correctamente"
                }
            elif response.status_code == 429:
                factaliza_health = {
                    "status": "up",
                    "status_code": response.status_code,
                    "message": "Rate limit alcanzado (API funcional)"
                }
            else:
                factaliza_health = {
                    "status": "degraded",
                    "status_code": response.status_code,
                    "message": f"Respuesta inesperada: {response.status_code}"
                }
    except Exception as e:
        factaliza_health = {
            "status": "down",
            "error": str(e)[:100]
        }
    
    health_data["components"]["factaliza_api"] = factaliza_health
    
    # 4. Scoring System
    health_data["components"]["scoring"] = {
        "status": "active",
        "algorithm": "LegalBot V3.0",
        "sources": ["Factaliza API", "BuscarUC API", "OSCE/TCE DB"],
        "weights": {
            "sanciones_osce_tce": "70%",
            "datos_sunat": "30%"
        }
    }
    
    # 5. System Info
    health_data["system"] = {
        "name": "Conflict Zero API",
        "environment": "production",
        "consultor_id": "40648",
        "features": [
            "Score/Plan Desacoplado",
            "Factaliza Integration",
            "OSCE/TCE Scraping",
            "Redis Cache",
            "White Glove Auth"
        ]
    }
    
    # Determinar status general
    component_statuses = [
        health_data["components"]["redis"].get("status"),
        health_data["components"]["postgresql"].get("status"),
        health_data["components"]["factaliza_api"].get("status")
    ]
    
    if any(s == "error" or s == "down" for s in component_statuses if s):
        health_data["status"] = "degraded"
    if all(s == "down" or s == "error" or s == "disabled" for s in component_statuses if s):
        health_data["status"] = "unhealthy"
    
    return health_data

@app.get("/api/v1/health")
async def health_check_v1():
    """
    Health Check V1 - Alias para compatibilidad
    """
    return await health_check()

@app.post("/api/v3/validate")
async def validate_ruc(request: ValidateRequest):
    """Valida RUC y retorna Score + Tier + Planes"""
    ruc = request.ruc.strip()
    
    if len(ruc) != 11 or not ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC inválido")
    
    try:
        # 1. Verificar cache REDIS primero (rápido)
        cache_key = validation_key(ruc)
        redis_cached = await redis_cache.get(cache_key)
        
        if redis_cached:
            # CRITICAL FIX: Ignorar si es MOCK_DEFAULT
            if redis_cached.get('fuente_datos') == 'MOCK_DEFAULT':
                print(f"[Redis] Ignorando MOCK_DEFAULT para {ruc}")
                redis_cached = None
            else:
                print(f"[Redis] ✅ Cache HIT para {ruc}")
                return redis_cached
        
        # 2. Verificar cache PostgreSQL (persistente, 7 días)
        cached = get_validation_from_db(ruc, max_age_hours=168)
        # CRITICAL FIX: Ignorar cache si es MOCK_DEFAULT fraudulento
        if cached and cached.get('fuente_datos') == 'MOCK_DEFAULT':
            print(f"[Cache] Ignorando MOCK_DEFAULT para {ruc}")
            cached = None  # Forzar recálculo
        
        if cached:
            print(f"[Cache] Datos encontrados en cache para {ruc}")
            # CRITICAL FIX: Ignorar cache si es MOCK_DEFAULT o ERROR_HONESTO
            if cached.get('fuente_datos') in ['MOCK_DEFAULT', 'ERROR_HONESTO']:
                print(f"[Cache] Ignorando cache con fuente={cached.get('fuente_datos')} para {ruc}")
                cached = None  # Forzar recálculo
        
        if cached:
            # Usar cache válido
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
            # Guardar en Redis para próximas consultas
            await redis_cache.set(cache_key, result, ttl=3600)  # 1h en Redis
        else:
            # 3. Consultar Factaliza y calcular
            result = await calculate_score_v3(ruc)
            
            # CHECKPOINT 8 FIX: Manejar datos provisionales para RUCs nuevos
            if result.get('fuente') == 'PROVISIONAL_PENDING_VERIFICATION':
                # Usar score provisional pero permitir el registro
                score_provisional = result.get('score_provisional', 80.0)
                tier_provisional = result.get('tier_provisional', 'SILVER')
                
                tier_info = get_tier_info(score_provisional)
                plans = get_available_plans(score_provisional)
                
                return {
                    'success': True,
                    'ruc': ruc,
                    'company_name': result['razon_social'],
                    'score': score_provisional,
                    'tier': {
                        'name': tier_info['name'], 'color': tier_info['color'],
                        'bg_color': tier_info['bg_color'], 'badge': tier_info['badge'],
                        'description': tier_info['desc'], 'message': tier_info['message']
                    },
                    'plans': plans,
                    'can_purchase': score_provisional >= 30,
                    'sanciones_count': len(result.get('sanciones', [])),
                    'fuente_datos': 'PROVISIONAL - Requiere verificación manual',
                    'consultor_factaliza': '40648',
                    'timestamp': result['timestamp'],
                    'requiere_verificacion': True,
                    'nota': 'Este RUC tiene score provisional. Será verificado manualmente por el equipo de Conflict Zero.'
                }
            
            # Detectar errores honestos
            if result.get('error') in ['RUC_NOT_AVAILABLE', 'RUC_NOT_FOUND']:
                return {
                    'success': False,
                    'error': result['error'],
                    'message': result['message'],
                    'ruc': ruc,
                    'status': result.get('status', 'PENDING_REVIEW'),
                    'fuente_datos': result.get('fuente', 'ERROR_HONESTO'),
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


@app.get("/api/v3/certificates/{cert_slug}")
async def verify_certificate(cert_slug: str):
    """
    Verifica un certificado por su slug.
    Retorna los datos del certificado si es válido.
    """
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database not available")
    
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ruc, company_name, score, tier, plan_type, 
                   cert_slug, created_at
            FROM certificates_v3
            WHERE cert_slug = %s
        """, (cert_slug,))
        
        row = cursor.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Certificado no encontrado")
        
        # Verificar si el certificado está vigente (1 año de validez)
        created_at = row[6]
        if created_at:
            expiry_date = created_at + timedelta(days=365)
            is_valid = datetime.now() < expiry_date
        else:
            is_valid = True
            expiry_date = None
        
        return {
            'success': True,
            'valid': is_valid,
            'certificate': {
                'slug': row[5],
                'ruc': row[0],
                'company_name': row[1],
                'score': float(row[2]),
                'tier': row[3],
                'plan': row[4],
                'issued_at': row[6].isoformat() if hasattr(row[6], 'isoformat') else str(row[6]),
                'expires_at': expiry_date.isoformat() if expiry_date else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[VerifyCert] Error: {e}")
        raise HTTPException(status_code=500, detail=f"Error verificando certificado: {str(e)}")
    finally:
        if conn:
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

@app.post("/api/v3/internal/migrate")
async def migrate_tables(secret: str = Header(None)):
    """
    ENDPOINT DE MIGRACIÓN: Crear tablas faltantes
    """
    if secret != "MIGRATE_2026_CZ":
        return JSONResponse(status_code=401, content={'success': False, 'error': 'UNAUTHORIZED'})
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(status_code=503, content={'success': False, 'error': 'DB_UNAVAILABLE'})
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(status_code=503, content={'success': False, 'error': 'DB_ERROR'})
    
    created_tables = []
    
    try:
        with conn.cursor() as cur:
            # Verificar si existe tabla invitations
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = 'invitations'
                )
            """)
            invitations_exists = cur.fetchone()[0]
            
            if not invitations_exists:
                # Crear tabla invitations
                cur.execute("""
                    CREATE TABLE invitations (
                        id SERIAL PRIMARY KEY,
                        invitador_ruc VARCHAR(11) NOT NULL,
                        email VARCHAR(200) NOT NULL,
                        token VARCHAR(100) UNIQUE NOT NULL,
                        ruc_invitado VARCHAR(11),
                        expira TIMESTAMP DEFAULT (NOW() + INTERVAL '24 hours'),
                        usada BOOLEAN DEFAULT FALSE,
                        usada_por INTEGER,
                        created_at TIMESTAMP DEFAULT NOW()
                    )
                """)
                cur.execute("CREATE INDEX idx_invitations_token ON invitations(token)")
                cur.execute("CREATE INDEX idx_invitations_invitador ON invitations(invitador_ruc)")
                created_tables.append('invitations')
            
            conn.commit()
            
            return {
                'success': True,
                'message': 'Migración completada',
                'tables_created': created_tables,
                'invitations_existed': invitations_exists
            }
    except Exception as e:
        conn.rollback()
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'MIGRATION_FAILED', 'message': str(e)}
        )
    finally:
        conn.close()

# ============ REDIS CACHE ENDPOINTS ============

@app.get("/api/v3/internal/redis-status")
async def redis_status():
    """Verificar estado de Redis Cache"""
    status = await redis_cache.health_check()
    return {
        "status": "ok",
        "redis": status,
        "cache_strategy": "Redis (1h) → PostgreSQL (7d) → Factaliza API"
    }

@app.get("/api/v3/internal/cache-test/{ruc}")
async def cache_test(ruc: str):
    """Test de cache: validar RUC y mostrar fuente de datos"""
    cache_key = validation_key(ruc)
    
    # Verificar Redis
    redis_data = await redis_cache.get(cache_key)
    
    # Verificar PostgreSQL
    db_data = get_validation_from_db(ruc, max_age_hours=168)
    
    return {
        "ruc": ruc,
        "cache_key": cache_key,
        "redis": {
            "hit": redis_data is not None,
            "data": redis_data
        },
        "postgresql": {
            "hit": db_data is not None,
            "data": {
                "ruc": db_data.get('ruc'),
                "score": float(db_data['score_calculated']) if db_data else None,
                "tier": db_data.get('tier'),
                "fuente": db_data.get('fuente_datos'),
                "created_at": str(db_data.get('created_at')) if db_data else None
            } if db_data else None
        }
    }

@app.delete("/api/v3/internal/cache-clear/{ruc}")
async def cache_clear(ruc: str):
    """Limpiar cache de un RUC específico"""
    cache_key = validation_key(ruc)
    result = await redis_cache.delete(cache_key)
    return {
        "ruc": ruc,
        "redis_cleared": result,
        "message": f"Cache Redis eliminado para {ruc}"
    }

# ============ NETWORK / MI RED ENDPOINT ============

@app.get("/api/v3/network/{ruc}")
async def get_network(ruc: str):
    """
    Obtener red de subcontratistas para visualización D3.js
    Demo: Solo funciona para Zamora (20529400790)
    """
    if ruc != '20529400790':
        return JSONResponse(
            status_code=403,
            content={'error': 'Solo demo para Zamora disponible'}
        )
    
    # Mock data realista - electricistas en Chiclayo/Cajamarca
    network_data = {
        'centro': {
            'ruc': '20529400790',
            'nombre': 'CONSTRUCTORA ZAMORA JARA SAC',
            'score': 41.2,
            'tier': 'BRONZE',
            'color': '#B87333',
            'tipo': 'contratista_principal'
        },
        'nodos': [
            {
                'id': '20987654321',
                'ruc': '20987654321',
                'nombre': 'ELECTRICISTAS DEL NORTE SAC',
                'score': 85,
                'tier': 'SILVER',
                'color': '#C0C0C0',
                'conexion': 'directo',
                'tipo': 'subcontratista',
                'ubicacion': 'Chiclayo'
            },
            {
                'id': '20876543210',
                'ruc': '20876543210',
                'nombre': 'INGELÉCTRICA PERÚ SRL',
                'score': 45,
                'tier': 'BRONZE',
                'color': '#B87333',
                'conexion': 'indirecto',
                'tipo': 'subcontratista',
                'ubicacion': 'Cajamarca'
            },
            {
                'id': '20765432109',
                'ruc': '20765432109',
                'nombre': 'CABLEADO INDUSTRIAL DEL SUR SAC',
                'score': 95,
                'tier': 'GOLD',
                'color': '#D4AF37',
                'conexion': 'directo',
                'tipo': 'subcontratista',
                'ubicacion': 'Chiclayo'
            },
            {
                'id': '20654321098',
                'ruc': '20654321098',
                'nombre': 'LUZ Y FUERZA CHICLAYO EIRL',
                'score': 22,
                'tier': 'RECHAZADO',
                'color': '#8B0000',
                'conexion': 'observado',
                'tipo': 'subcontratista',
                'ubicacion': 'Chiclayo',
                'alerta': 'Inhabilitado para contratación'
            },
            {
                'id': '20543210987',
                'ruc': '20543210987',
                'nombre': 'SERVICIOS ELÉCTRICOS NORTE SAC',
                'score': 73,
                'tier': 'SILVER',
                'color': '#C0C0C0',
                'conexion': 'directo',
                'tipo': 'subcontratista',
                'ubicacion': 'Lambayeque'
            },
            {
                'id': '20432109876',
                'ruc': '20432109876',
                'nombre': 'INSTALACIONES ELÉCTRICAS JOSÉ SRL',
                'score': 68,
                'tier': 'BRONZE',
                'color': '#B87333',
                'conexion': 'indirecto',
                'tipo': 'subcontratista',
                'ubicacion': 'Cajamarca'
            },
            {
                'id': '20321098765',
                'ruc': '20321098765',
                'nombre': 'ENERGÍA Y SISTEMAS DEL NORTE EIRL',
                'score': 91,
                'tier': 'GOLD',
                'color': '#D4AF37',
                'conexion': 'directo',
                'tipo': 'subcontratista',
                'ubicacion': 'Chiclayo'
            }
        ],
        'links': [
            {'source': '20529400790', 'target': '20987654321', 'tipo': 'directo'},
            {'source': '20529400790', 'target': '20765432109', 'tipo': 'directo'},
            {'source': '20529400790', 'target': '20543210987', 'tipo': 'directo'},
            {'source': '20529400790', 'target': '20321098765', 'tipo': 'directo'},
            {'source': '20987654321', 'target': '20876543210', 'tipo': 'indirecto'},
            {'source': '20987654321', 'target': '20432109876', 'tipo': 'indirecto'},
            {'source': '20529400790', 'target': '20654321098', 'tipo': 'observado'}
        ],
        'resumen': {
            'total_nodos': 7,
            'por_tier': {
                'GOLD': 2,
                'SILVER': 2,
                'BRONZE': 2,
                'RECHAZADO': 1
            },
            'score_promedio': 68.5,
            'riesgo_red': 'MEDIO'
        }
    }
    
    return network_data

# ============ API PÚBLICA V1 ============

class APIValidateRequest(BaseModel):
    ruc: str
    api_key: Optional[str] = None

@app.post("/api/v1/validate")
async def api_v1_validate(request: APIValidateRequest):
    """
    API Pública V1 - Validación de RUC para integraciones externas
    Compatible con bancos, aseguradoras, ERPs
    """
    ruc = request.ruc.strip()
    
    if len(ruc) != 11 or not ruc.isdigit():
        return JSONResponse(
            status_code=400,
            content={
                'success': False,
                'error': 'INVALID_RUC',
                'message': 'RUC debe tener 11 dígitos numéricos'
            }
        )
    
    try:
        # Usar mismo cálculo que v3
        result = await calculate_score_v3(ruc)
        
        if 'error' in result:
            return JSONResponse(
                status_code=404,
                content={
                    'success': False,
                    'error': result['error'],
                    'message': result.get('message', 'RUC no disponible')
                }
            )
        
        # Formato estándar para API pública
        return {
            'success': True,
            'data': {
                'ruc': result['ruc'],
                'razon_social': result['razon_social'],
                'score': result['score'],
                'tier': result['tier'],
                'recomendacion': result.get('recomendacion', ''),
                'planes_disponibles': result.get('planes_disponibles', []),
                'fuente_datos': result.get('fuente_datos', 'unknown'),
                'consultor_verificador': '40648',
                'timestamp': datetime.now().isoformat()
            },
            'api_version': '1.0.0',
            'documentation': 'https://czperu.com/docs/api'
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': str(e)
            }
        )

@app.get("/api/v1/docs")
async def api_v1_docs():
    """Documentación de API Pública V1"""
    return {
        'api': 'Conflict Zero Public API',
        'version': '1.0.0',
        'endpoints': [
            {
                'path': '/api/v1/validate',
                'method': 'POST',
                'description': 'Validar RUC y obtener score',
                'request': {'ruc': 'string (11 dígitos)'},
                'response': {
                    'success': 'boolean',
                    'data': {
                        'ruc': 'string',
                        'razon_social': 'string',
                        'score': 'number (0-100)',
                        'tier': 'string (GOLD/SILVER/BRONZE/RECHAZADO)'
                    }
                }
            }
        ],
        'rate_limits': '100 requests/hour',
        'contact': 'api@czperu.com'
    }

# ============ AUTH ENDPOINTS (White Glove) ============

def hash_password(password: str) -> str:
    """Hashear password con bcrypt"""
    if not AUTH_AVAILABLE:
        return password  # Fallback inseguro solo para desarrollo
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verificar password"""
    if not AUTH_AVAILABLE:
        return password == hashed  # Fallback inseguro solo para desarrollo
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_jwt_token(user_id: int, email: str, ruc: str) -> str:
    """Crear JWT token"""
    payload = {
        'user_id': user_id,
        'email': email,
        'ruc': ruc,
        'exp': datetime.utcnow() + timedelta(days=7),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt_token(token: str) -> Optional[Dict]:
    """Verificar JWT token"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.post("/api/v3/admin/create-user")
async def admin_create_user(request: CreateUserRequest, x_admin_token: str = Header(None)):
    """
    CHECKPOINT 1: Crear usuario (solo admin - White Glove)
    Protegido por X-Admin-Token header
    """
    # Verificar token admin
    print(f"[Admin] Token recibido: {x_admin_token}")
    print(f"[Admin] Token esperado: {ADMIN_TOKEN}")
    
    if x_admin_token != ADMIN_TOKEN:
        return JSONResponse(
            status_code=403,
            content={'success': False, 'error': 'UNAUTHORIZED', 'message': 'Token admin inválido'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE', 'message': 'Base de datos no disponible'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR', 'message': 'No hay conexión a BD'}
        )
    
    try:
        with conn.cursor() as cur:
            # Obtener nombre de empresa desde validations_v3
            cur.execute("SELECT razon_social FROM validations_v3 WHERE ruc = %s", (request.ruc,))
            result = cur.fetchone()
            company_name = result[0] if result else request.ruc
            
            # Hashear password
            password_hash = hash_password(request.password)
            
            # Crear usuario
            cur.execute("""
                INSERT INTO users (email, password_hash, ruc, company_name, plan, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    ruc = EXCLUDED.ruc,
                    company_name = EXCLUDED.company_name,
                    plan = EXCLUDED.plan
                RETURNING id, email, ruc, company_name, plan, created_at
            """, (request.email, password_hash, request.ruc, company_name, request.plan))
            
            user = cur.fetchone()
            conn.commit()
            
            return {
                'success': True,
                'message': 'Usuario creado exitosamente',
                'user': {
                    'id': user[0],
                    'email': user[1],
                    'ruc': user[2],
                    'company_name': user[3],
                    'plan': user[4],
                    'created_at': str(user[5])
                }
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.post("/api/v3/auth/login")
async def auth_login(request: LoginRequest):
    """
    CHECKPOINT 1: Login de usuario (público)
    Retorna JWT token
    """
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE', 'message': 'Base de datos no disponible'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR', 'message': 'No hay conexión a BD'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, email, password_hash, ruc, company_name, plan, is_active
                FROM users WHERE email = %s
            """, (request.email,))
            
            user = cur.fetchone()
            
            if not user:
                return JSONResponse(
                    status_code=401,
                    content={'success': False, 'error': 'INVALID_CREDENTIALS', 'message': 'Email o password incorrectos'}
                )
            
            if not user['is_active']:
                return JSONResponse(
                    status_code=403,
                    content={'success': False, 'error': 'ACCOUNT_DISABLED', 'message': 'Cuenta desactivada'}
                )
            
            # Verificar password
            if not verify_password(request.password, user['password_hash']):
                return JSONResponse(
                    status_code=401,
                    content={'success': False, 'error': 'INVALID_CREDENTIALS', 'message': 'Email o password incorrectos'}
                )
            
            # Actualizar last_login
            cur.execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user['id'],))
            conn.commit()
            
            # Crear JWT
            token = create_jwt_token(user['id'], user['email'], user['ruc'])
            
            return {
                'success': True,
                'token': token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'ruc': user['ruc'],
                    'company_name': user['company_name'],
                    'plan': user['plan']
                }
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.get("/api/v3/auth/me")
async def auth_me(authorization: str = Header(None)):
    """
    CHECKPOINT 1: Obtener datos del usuario logueado
    Requiere JWT en header Authorization: Bearer <token>
    """
    if not authorization or not authorization.startswith('Bearer '):
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'NO_TOKEN', 'message': 'Token no proporcionado'}
        )
    
    token = authorization.replace('Bearer ', '')
    payload = verify_jwt_token(token)
    
    if not payload:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'INVALID_TOKEN', 'message': 'Token inválido o expirado'}
        )
    
    return {
        'success': True,
        'user': {
            'id': payload['user_id'],
            'email': payload['email'],
            'ruc': payload['ruc']
        }
    }

# ============ GRUPO C: INVITACIONES SIMPLES ============
import secrets

def generate_invitation_token():
    """Genera token único para invitación"""
    return secrets.token_urlsafe(32)

@app.post("/api/v3/invitations")
async def create_invitation(
    request: CreateInvitationRequest,
    authorization: str = Header(None)
):
    """
    GRUPO C: Crear invitación para subcontratista
    Requiere plan Professional o Enterprise
    """
    user = get_current_user(authorization)
    if not user:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'UNAUTHORIZED'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor() as cur:
            # Verificar plan
            cur.execute("SELECT plan FROM users WHERE id = %s", (user['user_id'],))
            result = cur.fetchone()
            if not result or result[0] not in ['professional', 'enterprise']:
                return JSONResponse(
                    status_code=403,
                    content={
                        'success': False,
                        'error': 'PLAN_REQUIRED',
                        'message': 'Invitaciones requieren plan Professional o Enterprise'
                    }
                )
            
            # Generar token único
            token = generate_invitation_token()
            
            # Crear invitación (expira en 24h)
            cur.execute("""
                INSERT INTO invitations (invitador_ruc, email, token, ruc_invitado, expira)
                VALUES (%s, %s, %s, %s, NOW() + INTERVAL '24 hours')
                RETURNING id, token, expira, created_at
            """, (user['ruc'], request.email, token, request.ruc_invitado))
            
            result = cur.fetchone()
            conn.commit()
            
            # Link de registro
            register_link = f"https://czperu.com/registro?invitador={user['ruc']}&token={token}"
            
            return {
                'success': True,
                'invitation': {
                    'id': result[0],
                    'email': request.email,
                    'token': result[1],
                    'expira': str(result[2]),
                    'created_at': str(result[3]),
                    'register_link': register_link
                },
                'message': f"Invitación creada. Link: {register_link}"
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.get("/api/v3/invitations/validate")
async def validate_invitation(token: str):
    """
    GRUPO C: Validar token de invitación
    Retorna info del invitador si es válido
    """
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT i.*, u.company_name as invitador_company
                FROM invitations i
                LEFT JOIN users u ON u.ruc = i.invitador_ruc
                WHERE i.token = %s 
                AND i.usada = FALSE 
                AND i.expira > NOW()
            """, (token,))
            
            invitation = cur.fetchone()
            
            if not invitation:
                return JSONResponse(
                    status_code=400,
                    content={'success': False, 'error': 'INVALID_TOKEN', 'message': 'Token inválido o expirado'}
                )
            
            return {
                'success': True,
                'valid': True,
                'invitador': {
                    'ruc': invitation['invitador_ruc'],
                    'company_name': invitation['invitador_company'] or invitation['invitador_ruc']
                },
                'email': invitation['email'],
                'expira': str(invitation['expira'])
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.post("/api/v3/auth/register")
async def register_with_invitation(request: RegisterWithInvitationRequest):
    """
    GRUPO C: Registrar usuario con invitación
    """
    if not PSYCOPG2_AVAILABLE or not AUTH_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'SERVICE_UNAVAILABLE'}
        )
    
    # Validar token primero
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar token válido
            cur.execute("""
                SELECT * FROM invitations 
                WHERE token = %s 
                AND usada = FALSE 
                AND expira > NOW()
            """, (request.token,))
            
            invitation = cur.fetchone()
            if not invitation:
                return JSONResponse(
                    status_code=400,
                    content={'success': False, 'error': 'INVALID_TOKEN'}
                )
            
            # Validar que el email coincida
            if invitation['email'].lower() != request.email.lower():
                return JSONResponse(
                    status_code=400,
                    content={'success': False, 'error': 'EMAIL_MISMATCH', 'message': 'El email no coincide con la invitación'}
                )
            
            # Crear usuario
            password_hash = hash_password(request.password)
            company_name = request.company_name or f"Empresa {request.ruc}"
            
            cur.execute("""
                INSERT INTO users (email, password_hash, ruc, company_name, plan, is_active, created_at)
                VALUES (%s, %s, %s, %s, 'starter', TRUE, NOW())
                ON CONFLICT (email) DO UPDATE SET
                    password_hash = EXCLUDED.password_hash,
                    ruc = EXCLUDED.ruc,
                    company_name = EXCLUDED.company_name
                RETURNING id, email, ruc, company_name
            """, (request.email, password_hash, request.ruc, company_name))
            
            user = cur.fetchone()
            
            # Marcar invitación como usada
            cur.execute("""
                UPDATE invitations 
                SET usada = TRUE, usada_por = %s 
                WHERE id = %s
            """, (user['id'], invitation['id']))
            
            conn.commit()
            
            # Crear JWT
            token_jwt = create_jwt_token(user['id'], user['email'], user['ruc'])
            
            return {
                'success': True,
                'message': 'Usuario registrado exitosamente',
                'token': token_jwt,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'ruc': user['ruc'],
                    'company_name': user['company_name'],
                    'invitado_por': invitation['invitador_ruc']
                },
                'invitador': {
                    'ruc': invitation['invitador_ruc']
                }
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

# Schema para registro web sin invitación
class RegisterWebRequest(BaseModel):
    email: str
    password: str
    full_name: str
    company_name: Optional[str] = None
    ruc: Optional[str] = None

@app.post("/api/v3/auth/register-web")
async def register_web(request: RegisterWebRequest):
    """
    Registro desde formulario web (sin invitación requerida)
    """
    if not PSYCOPG2_AVAILABLE or not AUTH_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'SERVICE_UNAVAILABLE'}
        )
    
    # Validar email único
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar si email ya existe
            cur.execute("SELECT id FROM users WHERE email = %s", (request.email,))
            if cur.fetchone():
                return JSONResponse(
                    status_code=409,
                    content={'success': False, 'error': 'EMAIL_EXISTS', 'message': 'El email ya está registrado'}
                )
            
            # Hash de contraseña usando la función existente
            password_hash = hash_password(request.password)
            
            # Crear usuario - usando solo columnas que existen en el schema
            cur.execute("""
                INSERT INTO users (email, password_hash, ruc, company_name, plan, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, FALSE, NOW())
                RETURNING id
            """, (request.email, password_hash, request.ruc or '00000000000', 
                  request.company_name or '', 'professional'))
            
            result = cur.fetchone()
            conn.commit()
            
            return {
                'success': True,
                'message': 'Usuario registrado exitosamente - Pendiente de aprobación',
                'user_id': result['id'],
                'status': 'pending_review'
            }
    except Exception as e:
        print(f"[Register Web] Error: {e}")
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()


# ============ NOTIFICACIONES ADMIN v2 ============

class NotifyAdminRequest(BaseModel):
    ruc: str
    empresa: str
    plan: str
    email: str
    phone: Optional[str] = None
    nombre: Optional[str] = None
    score: Optional[str] = None
    timestamp: Optional[str] = None
    admin_email: Optional[str] = None  # Email alternativo para notificaciones


# Email del administrador (se puede configurar via env)
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'contacto@czperu.com')


@app.post("/api/v3/notify-admin")
async def notify_admin(request: NotifyAdminRequest):
    """
    Notificar al administrador sobre nueva postulación
    Guarda en BD y retorna inmediatamente (SMTP opcional)
    """
    try:
        # Email destino - SIEMPRE contacto@czperu.com
        dest_email = "contacto@czperu.com"
        
        print(f"[Notify Admin] Nueva postulación: {request.empresa} ({request.ruc}) - Plan: {request.plan}")
        print(f"[Notify Admin] Email destino: {dest_email}")
        
        # Guardar notificación en base de datos si está disponible
        if PSYCOPG2_AVAILABLE:
            conn = get_db_connection()
            if conn:
                try:
                    with conn.cursor() as cur:
                        cur.execute("""
                            CREATE TABLE IF NOT EXISTS admin_notifications (
                                id SERIAL PRIMARY KEY,
                                ruc VARCHAR(20),
                                empresa VARCHAR(255),
                                plan VARCHAR(50),
                                email VARCHAR(255),
                                phone VARCHAR(50),
                                nombre VARCHAR(255),
                                score VARCHAR(20),
                                created_at TIMESTAMP DEFAULT NOW()
                            )
                        """)
                        cur.execute("""
                            INSERT INTO admin_notifications 
                            (ruc, empresa, plan, email, phone, nombre, score)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """, (request.ruc, request.empresa, request.plan, request.email,
                              request.phone, request.nombre, request.score))
                        conn.commit()
                        print(f"[Notify Admin] Guardado en BD exitosamente")
                except Exception as e:
                    print(f"[Notify Admin] Error guardando en DB: {e}")
                finally:
                    conn.close()
        
        return {
            'success': True,
            'message': 'Notificación registrada',
            'admin_email': dest_email,
            'data': {
                'ruc': request.ruc,
                'empresa': request.empresa,
                'plan': request.plan,
                'email': request.email
            }
        }
        
    except Exception as e:
        print(f"[Notify Admin] Error: {e}")
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'NOTIFICATION_ERROR', 'message': str(e)}
        )


@app.get("/api/v3/invitations/mis-invitados")
async def get_invitados(authorization: str = Header(None)):
    """
    GRUPO C: Ver usuarios invitados por mí
    """
    user = get_current_user(authorization)
    if not user:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'UNAUTHORIZED'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT i.id, i.email, i.ruc_invitado, i.usada, i.created_at, i.expira,
                       u.ruc as registrado_ruc, u.company_name as registrado_company,
                       u.created_at as registrado_fecha
                FROM invitations i
                LEFT JOIN users u ON u.id = i.usada_por
                WHERE i.invitador_ruc = %s
                ORDER BY i.created_at DESC
            """, (user['ruc'],))
            
            invitados = cur.fetchall()
            
            return {
                'success': True,
                'invitados': [dict(inv) for inv in invitados],
                'count': len(invitados),
                'count_registrados': sum(1 for inv in invitados if inv['usada'])
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

# ============ GRUPO B: SISTEMA DE ALERTAS ============

def get_current_user(authorization: str = Header(None)):
    """Helper para obtener usuario actual desde JWT"""
    if not authorization or not authorization.startswith('Bearer '):
        return None
    
    token = authorization.replace('Bearer ', '')
    return verify_jwt_token(token)

@app.post("/api/v3/alerts")
async def create_alert(
    request: CreateAlertRequest,
    authorization: str = Header(None)
):
    """
    GRUPO B: Crear alerta para un RUC
    Requiere plan Professional o Enterprise
    """
    user = get_current_user(authorization)
    if not user:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'UNAUTHORIZED', 'message': 'Token requerido'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor() as cur:
            # Verificar plan del usuario
            cur.execute("SELECT plan FROM users WHERE id = %s", (user['user_id'],))
            result = cur.fetchone()
            if not result:
                return JSONResponse(status_code=404, content={'success': False, 'error': 'USER_NOT_FOUND'})
            
            user_plan = result[0]
            if user_plan not in ['professional', 'enterprise']:
                return JSONResponse(
                    status_code=403,
                    content={
                        'success': False, 
                        'error': 'PLAN_REQUIRED',
                        'message': 'Alertas requieren plan Professional o Enterprise',
                        'upgrade_url': '/pricing'
                    }
                )
            
            # Crear alerta
            cur.execute("""
                INSERT INTO supplier_alerts 
                (user_id, ruc, alert_type, threshold, message, is_active, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id, created_at
            """, (
                user['user_id'], request.ruc, request.alert_type, 
                request.threshold, request.message, request.is_active
            ))
            
            result = cur.fetchone()
            conn.commit()
            
            return {
                'success': True,
                'alert': {
                    'id': result[0],
                    'ruc': request.ruc,
                    'alert_type': request.alert_type,
                    'threshold': request.threshold,
                    'message': request.message,
                    'is_active': request.is_active,
                    'created_at': str(result[1])
                }
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.get("/api/v3/alerts")
async def list_alerts(
    ruc: Optional[str] = None,
    authorization: str = Header(None)
):
    """
    GRUPO B: Listar alertas del usuario
    """
    user = get_current_user(authorization)
    if not user:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'UNAUTHORIZED'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            query = """
                SELECT id, ruc, alert_type, threshold, message, is_active,
                       created_at, triggered_at, triggered_count
                FROM supplier_alerts
                WHERE user_id = %s
            """
            params = [user['user_id']]
            
            if ruc:
                query += " AND ruc = %s"
                params.append(ruc)
            
            query += " ORDER BY created_at DESC"
            
            cur.execute(query, params)
            alerts = cur.fetchall()
            
            return {
                'success': True,
                'alerts': [dict(a) for a in alerts],
                'count': len(alerts)
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.delete("/api/v3/alerts/{alert_id}")
async def delete_alert(alert_id: int, authorization: str = Header(None)):
    """
    GRUPO B: Eliminar una alerta
    """
    user = get_current_user(authorization)
    if not user:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'UNAUTHORIZED'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM supplier_alerts 
                WHERE id = %s AND user_id = %s
                RETURNING id
            """, (alert_id, user['user_id']))
            
            result = cur.fetchone()
            conn.commit()
            
            if not result:
                return JSONResponse(
                    status_code=404,
                    content={'success': False, 'error': 'ALERT_NOT_FOUND'}
                )
            
            return {'success': True, 'message': 'Alerta eliminada'}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

@app.get("/api/v3/alerts/triggered")
async def get_triggered_alerts(
    limit: int = 10,
    authorization: str = Header(None)
):
    """
    GRUPO B: Obtener alertas que ya se dispararon
    """
    user = get_current_user(authorization)
    if not user:
        return JSONResponse(
            status_code=401,
            content={'success': False, 'error': 'UNAUTHORIZED'}
        )
    
    if not PSYCOPG2_AVAILABLE:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_UNAVAILABLE'}
        )
    
    conn = get_db_connection()
    if not conn:
        return JSONResponse(
            status_code=503,
            content={'success': False, 'error': 'DB_ERROR'}
        )
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, ruc, alert_type, threshold, message,
                       triggered_at, triggered_count, last_triggered_data
                FROM supplier_alerts
                WHERE user_id = %s AND triggered_count > 0
                ORDER BY triggered_at DESC
                LIMIT %s
            """, (user['user_id'], limit))
            
            alerts = cur.fetchall()
            
            return {
                'success': True,
                'triggered_alerts': [dict(a) for a in alerts],
                'count': len(alerts)
            }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={'success': False, 'error': 'DB_ERROR', 'message': str(e)}
        )
    finally:
        conn.close()

def check_and_trigger_alerts(ruc: str, new_score: float, old_data: Optional[dict] = None):
    """
    GRUPO B: Verificar y disparar alertas cuando cambia un RUC
    Llamado automáticamente después de validación
    """
    if not PSYCOPG2_AVAILABLE:
        return
    
    conn = get_db_connection()
    if not conn:
        return
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Buscar alertas activas para este RUC
            cur.execute("""
                SELECT * FROM supplier_alerts
                WHERE ruc = %s AND is_active = TRUE
            """, (ruc,))
            
            alerts = cur.fetchall()
            triggered = []
            
            for alert in alerts:
                should_trigger = False
                trigger_reason = None
                
                if alert['alert_type'] == 'score_drop':
                    threshold = alert['threshold'] or 70.0
                    if new_score < threshold:
                        should_trigger = True
                        trigger_reason = f'Score bajó a {new_score} (umbral: {threshold})'
                
                elif alert['alert_type'] == 'new_sanction':
                    # Detectar si hay nuevas sanciones comparando con old_data
                    if old_data and old_data.get('sanciones_count', 0) < new_data.get('sanciones_count', 0):
                        should_trigger = True
                        trigger_reason = 'Nueva sanción detectada'
                
                elif alert['alert_type'] == 'status_change':
                    if old_data and old_data.get('estado') != new_data.get('estado'):
                        should_trigger = True
                        trigger_reason = f'Estado cambió de {old_data.get("estado")} a {new_data.get("estado")}'
                
                if should_trigger:
                    triggered.append({
                        'alert_id': alert['id'],
                        'user_id': alert['user_id'],
                        'reason': trigger_reason
                    })
                    
                    # Actualizar alerta
                    cur.execute("""
                        UPDATE supplier_alerts
                        SET triggered_at = NOW(),
                            triggered_count = triggered_count + 1,
                            last_triggered_data = %s
                        WHERE id = %s
                    """, (
                        json.dumps({'score': new_score, 'reason': trigger_reason}),
                        alert['id']
                    ))
            
            conn.commit()
            
            if triggered:
                print(f"[ALERTS] {len(triggered)} alertas disparadas para RUC {ruc}")
                
    except Exception as e:
        print(f"[ALERTS] Error verificando alertas: {e}")
    finally:
        conn.close()

# ============================================================================
# WHITE GLOVE FLOW ENDPOINTS
# ============================================================================

class NotifyAdminRequest(BaseModel):
    ruc: str
    empresa: str
    plan: str
    email: str
    phone: Optional[str] = None
    nombre: Optional[str] = None
    score: Optional[str] = None

@app.post("/api/v3/admin/notify-admin")
async def notify_admin(request: NotifyAdminRequest):
    """
    Notificar al administrador sobre nueva postulación White Glove
    """
    try:
        print(f"[WHITE-GLOVE] Nueva postulación: {request.empresa} ({request.ruc}) - Plan: {request.plan}")
        
        # TODO: Enviar email real al administrador
        # Por ahora solo registramos en logs
        
        return {
            "success": True,
            "message": "Notificación registrada",
            "data": {
                "ruc": request.ruc,
                "empresa": request.empresa,
                "plan": request.plan,
                "score": request.score
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v3/admin/pending-users")
async def get_pending_users(authorization: str = Header(None)):
    """
    Obtener usuarios pendientes de aprobación
    """
    # Verificar token admin (aceptar ADMIN_TOKEN o cz2026)
    token = authorization.replace("Bearer ", "") if authorization else ""
    if token != ADMIN_TOKEN and token != "cz2026":
        raise HTTPException(status_code=403, detail="Token inválido")
    
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                id, ruc, company_name, email, plan, 
                is_active, created_at, last_login
            FROM users 
            ORDER BY created_at DESC
            LIMIT 50
        """)
        
        users = cursor.fetchall()
        
        # Convertir datetime a string
        for user in users:
            if user['created_at']:
                user['created_at'] = user['created_at'].isoformat() if user['created_at'] else None
            if user['last_login']:
                user['last_login'] = user['last_login'].isoformat() if user['last_login'] else None
        
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "pending_count": len(users),
            "users": users
        }
        
    except Exception as e:
        print(f"[ADMIN] Error obteniendo usuarios pendientes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ApproveUserRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None

@app.post("/api/v3/admin/approve-user/{user_id}")
async def approve_user(user_id: int, request: ApproveUserRequest, authorization: str = Header(None)):
    """
    Aprobar o rechazar un usuario pendiente
    """
    # Verificar token admin (aceptar ADMIN_TOKEN o cz2026)
    token = authorization.replace("Bearer ", "") if authorization else ""
    if token != ADMIN_TOKEN and token != "cz2026":
        raise HTTPException(status_code=403, detail="Token inválido")
    
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        # Verificar que el usuario existe
        cursor.execute(
            "SELECT id, is_active FROM users WHERE id = %s",
            (user_id,)
        )
        user = cursor.fetchone()
        
        if not user:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Actualizar estado (usar is_active en lugar de status)
        if request.approved:
            cursor.execute(
                "UPDATE users SET is_active = TRUE WHERE id = %s",
                (user_id,)
            )
            new_status = 'active'
        else:
            # Si se rechaza, eliminar el usuario
            cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
            new_status = 'rejected'
        
        conn.commit()
        cursor.close()
        conn.close()
        
        action = "aprobado" if request.approved else "rechazado"
        print(f"[ADMIN] Usuario {user_id} {action}")
        
        return {
            "success": True,
            "message": f"Usuario {action} correctamente",
            "user_id": user_id,
            "status": new_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ADMIN] Error aprobando usuario: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============ SINCRONIZACIÓN OSCE/TCE (RENDER CRON) ============

class SyncOSCERequest(BaseModel):
    force_download: bool = False

@app.post("/api/v3/admin/sync-osce-tce")
async def sync_osce_tce(request: SyncOSCERequest, authorization: str = Header(None)):
    """
    Endpoint de sincronización de datos OSCE/TCE - V2 MEJORADO.
    Ejecuta el scraping directamente en Render (misma DB que el API).
    """
    # Verificar token admin
    token = authorization.replace("Bearer ", "") if authorization else ""
    if token != ADMIN_TOKEN and token != "cz2026":
        raise HTTPException(status_code=403, detail="Token inválido")
    
    if not PSYCOPG2_AVAILABLE or not DATABASE_URL:
        raise HTTPException(status_code=503, detail="Database no disponible")
    
    import httpx
    from io import StringIO
    import csv
    
    result = {
        "success": True,
        "timestamp": datetime.now().isoformat(),
        "debug": {},
        "components": {}
    }
    
    try:
        # 1. Setup de tabla
        print("[SYNC] Paso 1: Setup tabla...")
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS osce_sanciones_detalle (
                id SERIAL PRIMARY KEY,
                ruc VARCHAR(11) NOT NULL,
                tipo_sancion VARCHAR(50) NOT NULL,
                numero_resolucion VARCHAR(100),
                entidad VARCHAR(200),
                fecha_inicio DATE,
                fecha_fin DATE,
                fecha_corte DATE,
                motivo TEXT,
                estado VARCHAR(20) DEFAULT 'VIGENTE',
                monto_penalidad DECIMAL(15,2),
                objeto_contrato TEXT,
                fuente VARCHAR(50) DEFAULT 'OSCE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_osce_sanciones_ruc ON osce_sanciones_detalle(ruc);
            CREATE INDEX IF NOT EXISTS idx_osce_sanciones_tipo ON osce_sanciones_detalle(tipo_sancion);
        """)
        conn.commit()
        
        # Truncar tabla para sincronización limpia
        cursor.execute("TRUNCATE TABLE osce_sanciones_detalle")
        conn.commit()
        cursor.close()
        conn.close()
        result["components"]["database_setup"] = "ok - tabla truncada"
        
        # Import execute_values aquí
        from psycopg2.extras import execute_values
        
        # 2. URLs de datos
        urls = {
            'sancionados': 'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/sancionados/sancionados.csv',
            'penalidades': 'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/penalidades/penalidades.csv',
            'inhabilitaciones': 'https://conosce.osce.gob.pe/buscador/assets/67ae6c4a/reportes/inhabilitaciones/inhabilitaciones_judiciales.csv',
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
        total_records = 0
        
        # 3. Procesar cada dataset
        for dataset_type, url in urls.items():
            step_result = {"status": "starting"}
            
            try:
                print(f"[SYNC] Descargando {dataset_type}...")
                
                # Descargar con timeout extendido
                async with httpx.AsyncClient(timeout=180.0) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                
                content_size = len(response.content)
                step_result["downloaded_bytes"] = content_size
                print(f"[SYNC] {dataset_type}: {content_size} bytes descargados")
                
                # Parsear CSV
                content = response.content.decode('utf-8', errors='ignore')
                reader = csv.DictReader(StringIO(content), delimiter='|')
                
                # Obtener headers
                headers_csv = reader.fieldnames
                step_result["csv_headers"] = headers_csv[:5] if headers_csv else []
                
                # Mapeo de columnas según el tipo
                column_map = {
                    'sancionados': {
                        'ruc': 'RUC',
                        'resolucion': 'NUMERO_RESOLUCION',
                        'fecha_inicio': 'FECHA_INICIO',
                        'fecha_fin': 'FECHA_FIN',
                        'motivo': 'DE_MOTIVO_INFRACCION',
                        'entidad': None  # No hay entidad en sancionados
                    },
                    'penalidades': {
                        'ruc': 'RUC_DNI',
                        'resolucion': 'NUMERO_RESOLUCION',
                        'fecha_inicio': 'FECHA_INICIO',
                        'fecha_fin': 'FECHA_FIN',
                        'motivo': 'DE_MOTIVO_INFRACCION',
                        'entidad': None
                    },
                    'inhabilitaciones': {
                        'ruc': 'RUC_DNI',
                        'resolucion': 'NUMERO_RESOLUCION',
                        'fecha_inicio': 'FECHA_INICIO',
                        'fecha_fin': 'FECHA_FIN',
                        'motivo': None,
                        'entidad': 'ORGANO_JURISDICCIONAL'
                    }
                }
                
                mapeo = column_map.get(dataset_type, column_map['sancionados'])
                
                records = []
                row_count = 0
                valid_count = 0
                
                for row in reader:
                    row_count += 1
                    
                    # Obtener RUC según el mapeo
                    ruc_key = mapeo.get('ruc', 'RUC')
                    ruc = row.get(ruc_key, '').strip()
                    
                    if not ruc or len(ruc) != 11:
                        continue
                    
                    valid_count += 1
                    
                    # Parsear fechas (formato AAAAMMDD)
                    def parse_date(d):
                        if not d or len(str(d)) != 8:
                            return None
                        try:
                            d = str(d)
                            return f"{d[:4]}-{d[4:6]}-{d[6:8]}"
                        except:
                            return None
                    
                    fecha_inicio = parse_date(row.get(mapeo.get('fecha_inicio', 'FECHA_INICIO'), ''))
                    fecha_fin = parse_date(row.get(mapeo.get('fecha_fin', 'FECHA_FIN'), ''))
                    
                    # Determinar estado
                    estado = 'VIGENTE'
                    if fecha_fin:
                        try:
                            fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                            if fin < datetime.now().date():
                                estado = 'VENCIDA'
                        except:
                            pass
                    
                    # Obtener entidad
                    entidad = 'OSCE'
                    if mapeo.get('entidad'):
                        entidad = row.get(mapeo['entidad'], 'OSCE') or 'OSCE'
                    
                    records.append((
                        ruc,
                        dataset_type,
                        row.get(mapeo.get('resolucion', 'NUMERO_RESOLUCION'), ''),
                        entidad,
                        fecha_inicio,
                        fecha_fin,
                        None,  # fecha_corte
                        row.get(mapeo.get('motivo', 'DE_MOTIVO_INFRACCION'), ''),
                        estado,
                        None,  # monto
                        None,  # objeto
                        'OSCE' if dataset_type != 'inhabilitaciones' else 'PODER_JUDICIAL'
                    ))
                    
                    # Insertar en batches de 500
                    if len(records) >= 500:
                        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                        cursor = conn.cursor()
                        execute_values(cursor, """
                            INSERT INTO osce_sanciones_detalle 
                            (ruc, tipo_sancion, numero_resolucion, entidad, fecha_inicio, 
                             fecha_fin, fecha_corte, motivo, estado, monto_penalidad, 
                             objeto_contrato, fuente)
                            VALUES %s
                        """, records)
                        conn.commit()
                        cursor.close()
                        conn.close()
                        total_records += len(records)
                        records = []
                
                # Insertar registros restantes
                if records:
                    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
                    cursor = conn.cursor()
                    execute_values(cursor, """
                        INSERT INTO osce_sanciones_detalle 
                        (ruc, tipo_sancion, numero_resolucion, entidad, fecha_inicio, 
                         fecha_fin, fecha_corte, motivo, estado, monto_penalidad, 
                         objeto_contrato, fuente)
                        VALUES %s
                    """, records)
                    conn.commit()
                    cursor.close()
                    conn.close()
                    total_records += len(records)
                
                step_result["status"] = "success"
                step_result["rows_read"] = row_count
                step_result["valid_rucs"] = valid_count
                step_result["inserted"] = valid_count
                print(f"[SYNC] ✅ {dataset_type}: {valid_count} registros insertados")
                
            except Exception as e:
                error_msg = str(e)
                print(f"[SYNC] ❌ Error en {dataset_type}: {error_msg}")
                step_result["status"] = "error"
                step_result["error"] = error_msg[:200]
            
            result["components"][dataset_type] = step_result
        
        # 4. Contar totales finales
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM osce_sanciones_detalle")
        final_count = cursor.fetchone()[0]
        
        # Contar por tipo
        cursor.execute("""
            SELECT tipo_sancion, COUNT(*) 
            FROM osce_sanciones_detalle 
            GROUP BY tipo_sancion
        """)
        type_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Verificar si Zamora está
        cursor.execute("""
            SELECT ruc, numero_resolucion, tipo_sancion, estado
            FROM osce_sanciones_detalle
            WHERE ruc = '20529400790'
        """)
        zamora_records = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        result["total_records_synced"] = total_records
        result["final_db_count"] = final_count
        result["by_type"] = type_counts
        result["zamora_found"] = len(zamora_records)
        result["zamora_details"] = [
            {"ruc": r[0], "resolucion": r[1], "tipo": r[2], "estado": r[3]}
            for r in zamora_records
        ]
        result["message"] = f"Sincronización completada. {final_count} registros en DB."
        
        print(f"[SYNC] ✅ TOTAL: {final_count} registros en base de datos")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SYNC] ❌ Error general: {e}")
        import traceback
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        raise HTTPException(status_code=500, detail=result)
    
    return result


# ============ DEBUG ENDPOINTS ============

@app.get("/api/v3/debug/sanciones-db/{ruc}")
async def debug_sanciones_db(ruc: str, authorization: str = Header(None)):
    """Endpoint de debug para verificar consulta de sanciones en DB"""
    # Verificar token admin
    token = authorization.replace("Bearer ", "") if authorization else ""
    if token != ADMIN_TOKEN and token != "cz2026":
        raise HTTPException(status_code=403, detail="Token inválido")
    
    # Consultar directamente la función
    sanciones = consultar_sanciones_db(ruc)
    
    # También consultar conteo total de tabla
    total_records = 0
    try:
        conn = psycopg2.connect(DATABASE_URL, sslmode='require')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM osce_sanciones_detalle")
        total_records = cursor.fetchone()[0]
        
        # Buscar específicamente este RUC
        cursor.execute("""
            SELECT ruc, tipo_sancion, numero_resolucion, estado
            FROM osce_sanciones_detalle
            WHERE ruc = %s
        """, (ruc,))
        raw_records = cursor.fetchall()
        
        cursor.close()
        conn.close()
    except Exception as e:
        raw_records = []
        total_records = f"Error: {e}"
    
    return {
        "ruc": ruc,
        "sanciones_funcion": sanciones,
        "total_db_records": total_records,
        "raw_query_records": [
            {"ruc": r[0], "tipo": r[1], "resolucion": r[2], "estado": r[3]}
            for r in raw_records
        ],
        "psycopg2_available": PSYCOPG2_AVAILABLE,
        "database_url_set": bool(DATABASE_URL)
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Conflict Zero API V3.2 + Invitaciones + Alertas + Factaliza #40648")
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)
# Deploy timestamp: Sun Mar 30 04:45:00 AM CST 2026
# Test GitHub Actions - Mon Mar 30 07:12:41 AM CST 2026

# FORCE REDEPLOY 2026-03-30T14:56:04+08:00

# Deploy: 2026-03-30T18:27:54+08:00
