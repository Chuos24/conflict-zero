"""
Redis Cache Module - Conflict Zero API V3
Cache de 2 niveles: Redis (rápido) → PostgreSQL (persistente)
"""
import json
import os
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

# Intentar importar redis, si no está disponible usar modo mock
try:
    import redis.asyncio as aioredis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[Redis] aioredis no disponible, usando modo mock")

class RedisCache:
    """Cache Redis con fallback a PostgreSQL"""
    
    def __init__(self):
        self.redis: Optional[Any] = None
        self.enabled = False
        self.default_ttl = int(os.getenv('REDIS_CACHE_TTL', '86400'))  # 24h default
        
    async def connect(self):
        """Conectar a Redis"""
        if not REDIS_AVAILABLE:
            print("[Redis] Modo mock - no hay conexión")
            return
            
        redis_url = os.getenv('REDIS_URL')
        if not redis_url:
            # Intentar construir desde variables Render
            redis_host = os.getenv('REDISHOST', 'localhost')
            redis_port = int(os.getenv('REDISPORT', '6379'))
            redis_password = os.getenv('REDISPASSWORD', '')
            
            if redis_password:
                redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}"
            else:
                redis_url = f"redis://{redis_host}:{redis_port}"
        
        try:
            self.redis = await aioredis.from_url(
                redis_url,
                encoding='utf-8',
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            # Test connection
            await self.redis.ping()
            self.enabled = True
            print(f"[Redis] ✅ Conectado - TTL: {self.default_ttl}s")
        except Exception as e:
            print(f"[Redis] ⚠️ No conectado: {e}")
            self.redis = None
            self.enabled = False
    
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Obtener valor del cache"""
        if not self.enabled or not self.redis:
            return None
            
        try:
            data = await self.redis.get(key)
            if data:
                print(f"[Redis] ✅ Cache HIT: {key}")
                return json.loads(data)
            print(f"[Redis] Cache MISS: {key}")
            return None
        except Exception as e:
            print(f"[Redis] Error GET: {e}")
            return None
    
    async def set(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Guardar valor en cache"""
        if not self.enabled or not self.redis:
            return False
            
        try:
            ttl = ttl or self.default_ttl
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value, default=str)
            )
            print(f"[Redis] 💾 Guardado: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            print(f"[Redis] Error SET: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Eliminar valor del cache"""
        if not self.enabled or not self.redis:
            return False
            
        try:
            await self.redis.delete(key)
            print(f"[Redis] 🗑️ Eliminado: {key}")
            return True
        except Exception as e:
            print(f"[Redis] Error DELETE: {e}")
            return False
    
    async def get_or_set(self, key: str, factory, ttl: Optional[int] = None):
        """Get o computar y guardar si no existe"""
        cached = await self.get(key)
        if cached is not None:
            return cached
            
        # Computar
        value = await factory() if asyncio.iscoroutinefunction(factory) else factory()
        if value:
            await self.set(key, value, ttl)
        return value
    
    async def health_check(self) -> Dict[str, Any]:
        """Verificar estado de Redis"""
        if not self.enabled or not self.redis:
            return {"status": "disabled", "connected": False}
            
        try:
            start = datetime.now()
            await self.redis.ping()
            latency = (datetime.now() - start).total_seconds() * 1000
            info = await self.redis.info()
            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": round(latency, 2),
                "version": info.get('redis_version', 'unknown'),
                "used_memory_human": info.get('used_memory_human', 'unknown'),
                "connected_clients": info.get('connected_clients', 0)
            }
        except Exception as e:
            return {"status": "error", "connected": False, "error": str(e)}

# Singleton global
redis_cache = RedisCache()

# Key generators
def validation_key(ruc: str) -> str:
    return f"validation:{ruc}"

def rate_limit_key(client_id: str) -> str:
    return f"rate_limit:{client_id}"

def queue_key(job_type: str) -> str:
    return f"queue:{job_type}"

# Rate limiting
class RateLimiter:
    """Rate limiting con Redis"""
    
    def __init__(self, cache: RedisCache):
        self.cache = cache
    
    async def is_allowed(self, client_id: str, max_requests: int = 100, window_seconds: int = 3600) -> tuple:
        """
        Verificar si cliente puede hacer request
        Returns: (allowed: bool, remaining: int, reset_time: int)
        """
        if not self.cache.enabled:
            return True, 999, 0
            
        try:
            key = rate_limit_key(client_id)
            pipe = self.cache.redis.pipeline()
            
            # Incrementar contador
            now = datetime.now().timestamp()
            pipe.incr(key)
            pipe.expire(key, window_seconds)
            
            results = await pipe.execute()
            current_count = results[0]
            
            remaining = max(0, max_requests - current_count)
            reset_time = int(now + window_seconds)
            
            allowed = current_count <= max_requests
            
            if not allowed:
                print(f"[RateLimit] 🚫 Bloqueado: {client_id} ({current_count}/{max_requests})")
            
            return allowed, remaining, reset_time
            
        except Exception as e:
            print(f"[RateLimit] Error: {e}")
            return True, 999, 0  # Permitir en caso de error

# Job Queue
class JobQueue:
    """Cola de jobs con Redis"""
    
    def __init__(self, cache: RedisCache):
        self.cache = cache
    
    async def enqueue(self, queue_name: str, job_data: Dict[str, Any]) -> str:
        """Agregar job a la cola"""
        if not self.cache.enabled:
            return "mock_job_id"
            
        job_id = f"{queue_name}:{datetime.now().timestamp()}"
        job_data['job_id'] = job_id
        job_data['status'] = 'pending'
        job_data['created_at'] = datetime.now().isoformat()
        
        await self.cache.redis.lpush(f"queue:{queue_name}", json.dumps(job_data))
        print(f"[Queue] 📥 Job encolado: {job_id}")
        return job_id
    
    async def dequeue(self, queue_name: str) -> Optional[Dict[str, Any]]:
        """Obtener siguiente job de la cola"""
        if not self.cache.enabled:
            return None
            
        data = await self.cache.redis.brpop(f"queue:{queue_name}", timeout=1)
        if data:
            job = json.loads(data[1])
            print(f"[Queue] 📤 Job procesando: {job.get('job_id')}")
            return job
        return None
    
    async def get_queue_length(self, queue_name: str) -> int:
        """Obtener longitud de cola"""
        if not self.cache.enabled:
            return 0
        return await self.cache.redis.llen(f"queue:{queue_name}")

# Import asyncio para get_or_set
import asyncio
