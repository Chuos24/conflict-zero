import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey, Text
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    ruc = Column(String(11), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    plan_type = Column(String(50), default="essential")
    api_key = Column(String(255), unique=True, nullable=True)
    monthly_requests = Column(Integer, default=0)
    monthly_limit = Column(Integer, default=1000)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verification_requests = relationship("VerificationRequest", back_populates="user")

class VerificationRequest(Base):
    __tablename__ = "verification_requests"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    ruc = Column(String(11), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    
    # Datos SUNAT
    sunat_debt = Column(Float, default=0.0)
    sunat_score_contribution = Column(Float, default=0.0)
    
    # Datos OSCE
    osce_sanctions_count = Column(Integer, default=0)
    osce_score_contribution = Column(Float, default=0.0)
    osce_sanctions_details = Column(JSON, default=list)
    
    # Datos TCE
    tce_sanctions_count = Column(Integer, default=0)
    tce_score_contribution = Column(Float, default=0.0)
    tce_sanctions_details = Column(JSON, default=list)
    
    # ML Score
    ml_anomaly_score = Column(Float, default=0.0)
    ml_score_contribution = Column(Float, default=0.0)
    
    # Metadata
    raw_data = Column(JSON, default=dict)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="verification_requests")

class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    level = Column(String(20), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)
    meta_data = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
