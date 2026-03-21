import os
from functools import lru_cache

class Settings:
    # App
    APP_NAME: str = os.getenv("APP_NAME", "Conflict Zero API")
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    VERSION: str = os.getenv("VERSION", "1.0.0")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./conflictzero.db")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # JWT
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 días por defecto
    
    # APIs Externas
    PERUAPI_TOKEN: str = os.getenv("PERUAPI_TOKEN", "")
    DECOLECTA_API_KEY: str = os.getenv("DECOLECTA_API_KEY", "")
    DECOLECTA_BASE_URL: str = os.getenv("DECOLECTA_BASE_URL", "https://api.decolecta.com")
    PERU_API_KEY: str = os.getenv("PERU_API_KEY", "")
    
    # AWS
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "conflictzero-certificados-prod")
    
    # Scoring
    SCORE_SUNAT_WEIGHT: float = float(os.getenv("SCORE_SUNAT_WEIGHT", "0.30"))
    SCORE_OSCE_WEIGHT: float = float(os.getenv("SCORE_OSCE_WEIGHT", "0.40"))
    SCORE_ML_WEIGHT: float = float(os.getenv("SCORE_ML_WEIGHT", "0.30"))
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
    RATE_LIMIT_WINDOW: int = int(os.getenv("RATE_LIMIT_WINDOW", "60"))
    
    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ALLOWED_HOSTS: str = os.getenv("ALLOWED_HOSTS", "*")
    USE_CACHE: bool = os.getenv("USE_CACHE", "false").lower() == "true"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
