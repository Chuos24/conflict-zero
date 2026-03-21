from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # App
    APP_NAME: str = "Conflict Zero API"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost/conflictzero"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # APIs Externas - Datos reales obligatorios
    PERUAPI_TOKEN: str = ""  # Primaria - https://peruapi.com
    DECOLECTA_API_KEY: str = ""  # Fallback - https://decolecta.com
    DECOLECTA_BASE_URL: str = "https://api.decolecta.com"
    
    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET: str = "conflictzero-certificados-prod"
    
    # Scoring
    SCORE_SUNAT_WEIGHT: float = 0.30
    SCORE_OSCE_WEIGHT: float = 0.40
    SCORE_ML_WEIGHT: float = 0.30
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    
    # Stripe (para pagos)
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()
