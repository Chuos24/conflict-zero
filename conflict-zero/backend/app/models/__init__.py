import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey, Text, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    ruc = Column(String(11), nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    plan_type = Column(String(50), default="free")  # free, starter, pro, enterprise
    api_key = Column(String(255), unique=True, nullable=True)
    monthly_requests = Column(Integer, default=0)
    monthly_limit = Column(Integer, default=100)  # free tier
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    verification_requests = relationship("VerificationRequest", back_populates="user")

class VerificationRequest(Base):
    __tablename__ = "verification_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ruc = Column(String(11), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)  # low, medium, high, critical
    
    # Datos SUNAT
    sunat_debt = Column(Float, default=0.0)
    sunat_score_contribution = Column(Float, default=0.0)
    
    # Datos OSCE
    osce_sanctions_count = Column(Integer, default=0)
    osce_score_contribution = Column(Float, default=0.0)
    osce_sanctions_details = Column(JSONB, default=list)
    
    # Datos TCE
    tce_sanctions_count = Column(Integer, default=0)
    tce_score_contribution = Column(Float, default=0.0)
    tce_sanctions_details = Column(JSONB, default=list)
    
    # ML Score
    ml_anomaly_score = Column(Float, default=0.0)
    ml_score_contribution = Column(Float, default=0.0)
    
    # Metadata
    raw_data = Column(JSONB, default=dict)
    pdf_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="verification_requests")

class ApiKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(255), unique=True, nullable=False)
    name = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

class SystemLog(Base):
    __tablename__ = "system_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    level = Column(String(20), nullable=False)  # info, warning, error
    message = Column(Text, nullable=False)
    source = Column(String(100), nullable=True)
    metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
