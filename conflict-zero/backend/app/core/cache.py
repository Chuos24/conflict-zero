import json
import redis
from typing import Optional, Any
from app.core.config import get_settings

settings = get_settings()

class Cache:
    def __init__(self):
        self._redis: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True
            )
        return self._redis
    
    def get(self, key: str) -> Optional[Any]:
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except redis.ConnectionError:
            return None
    
    def set(self, key: str, value: Any, expire: int = 3600) -> bool:
        try:
            self.client.setex(key, expire, json.dumps(value))
            return True
        except redis.ConnectionError:
            return False
    
    def delete(self, key: str) -> bool:
        try:
            self.client.delete(key)
            return True
        except redis.ConnectionError:
            return False
    
    def exists(self, key: str) -> bool:
        try:
            return self.client.exists(key) > 0
        except redis.ConnectionError:
            return False

cache = Cache()
