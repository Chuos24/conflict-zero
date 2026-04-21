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
    plan_type = Column(String(50), default="essential")  # essential, starter, professional, enterprise
    plan = Column(String(50), default="free")  # free, starter, professional, enterprise
    plan_activated_at = Column(DateTime, nullable=True)
    plan_expires_at = Column(DateTime, nullable=True)
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


# ============================================================================
# ML-READY: Company Snapshots (Time-Series para entrenamiento futuro)
# Guardamos el estado de cada empresa en cada consulta para ML posterior
# ============================================================================

class CompanySnapshot(Base):
    """
    Time-series de estados de empresas para ML predictivo.
    Cada fila es una "foto" del estado de una empresa en un momento dado.
    """
    __tablename__ = "company_snapshots"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ruc = Column(String(11), nullable=False, index=True)
    snapshot_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # --- Datos SUNAT (Time-Series) ---
    sunat_status = Column(String(20), nullable=True)  # ACTIVO, SUSPENDIDO, etc.
    sunat_debt = Column(Float, default=0.0)
    sunat_num_trabajadores = Column(Integer, nullable=True)
    sunat_ultimo_pago = Column(DateTime, nullable=True)
    
    # --- Datos OSCE (Time-Series) ---
    osce_inhabilitado = Column(Boolean, default=False)
    osce_sanciones_count = Column(Integer, default=0)
    osce_sanciones_vigentes = Column(Integer, default=0)
    osce_sanciones_historicas = Column(Integer, default=0)
    osce_ultima_sancion_fecha = Column(DateTime, nullable=True)
    
    # --- Datos TCE (Time-Series) ---
    tce_sanciones_count = Column(Integer, default=0)
    tce_ultima_sancion_fecha = Column(DateTime, nullable=True)
    
    # --- Features calculadas (para ML futuro) ---
    dias_ultimo_pago = Column(Integer, nullable=True)
    dias_ultima_sancion_osce = Column(Integer, nullable=True)
    score_calculado = Column(Integer, nullable=True)
    
    # --- Metadata ---
    source_api = Column(String(50), nullable=True)  # 'sunat', 'osce', 'decolecta', 'manual'
    query_id = Column(String(36), ForeignKey("verification_requests.id"), nullable=True)
    raw_data_hash = Column(String(64), nullable=True)  # Para detectar cambios
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Índice compuesto para consultas ML: RUC + fecha
    __table_args__ = (
        # Index para consultas time-series por empresa
        {'mysql_charset': 'utf8mb4'},
    )


class MlTrainingLog(Base):
    """
    Log de entrenamientos de modelos ML.
    Placeholder para cuando activemos ML en Mes 3-6.
    """
    __tablename__ = "ml_training_logs"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    model_version = Column(String(20), nullable=False)
    training_date = Column(DateTime, default=datetime.utcnow)
    dataset_size = Column(Integer, nullable=False)  # Número de snapshots usados
    accuracy = Column(Float, nullable=True)  # Precisión del modelo
    precision = Column(Float, nullable=True)
    recall = Column(Float, nullable=True)
    f1_score = Column(Float, nullable=True)
    feature_importance = Column(JSON, default=dict)  # Qué features pesan más
    model_path = Column(String(500), nullable=True)  # S3/local path al .pkl
    is_active = Column(Boolean, default=False)  # Este modelo está en producción?
    notes = Column(Text, nullable=True)


class NetworkWatchlist(Base):
    """
    Lista de proveedores monitoreados por cada usuario (Mi Red).
    """
    __tablename__ = "network_watchlist"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    ruc = Column(String(11), nullable=False, index=True)
    alias = Column(String(255), nullable=False)
    last_score = Column(Integer, nullable=True)
    last_status = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class NetworkAlert(Base):
    """
    Alertas de cambio de estado para proveedores en watchlist.
    """
    __tablename__ = "network_alerts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    ruc = Column(String(11), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False)
    old_status = Column(String(255), nullable=True)
    new_status = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)


class SupplierAlert(Base):
    """
    Alertas automáticas cuando un proveedor cambia de estado.
    Valor inmediato sin ser ML (detección de cambio simple).
    """
    __tablename__ = "supplier_alerts"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    supplier_ruc = Column(String(11), nullable=False, index=True)
    supplier_name = Column(String(255), nullable=True)
    
    # Cambio detectado
    change_type = Column(String(50), nullable=False)  # 'osce_inhabilitado', 'sunat_deuda', etc.
    previous_status = Column(String(255), nullable=True)
    new_status = Column(String(255), nullable=True)
    severity = Column(String(20), default="medium")  # low, medium, high, critical
    
    # Estado de la alerta
    is_read = Column(Boolean, default=False)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# INVITATIONS: Sistema de invitaciones para subcontratistas
# ============================================================================

class Invitation(Base):
    """
    Invitaciones enviadas a subcontratistas para unirse a la plataforma.
    """
    __tablename__ = "invitations"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    ruc = Column(String(11), nullable=True, index=True)
    company = Column(String(255), nullable=True)
    invited_by = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    token = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), default="pending")  # pending, accepted, expired, revoked
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    accepted_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)


# ============================================================================
# CERTIFICATES: Certificados de verificación generados
# ============================================================================

class Certificate(Base):
    """
    Certificados de verificación generados para empresas.
    Cada certificado tiene un código único para validación pública.
    """
    __tablename__ = "certificates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(16), unique=True, nullable=False, index=True)
    ruc = Column(String(11), nullable=False, index=True)
    company_name = Column(String(255), nullable=True)
    score = Column(Integer, nullable=False)
    risk_level = Column(String(20), nullable=False)
    
    # Datos del certificado
    sunat_status = Column(String(50), nullable=True)
    osce_sanctions_count = Column(Integer, default=0)
    tce_sanctions_count = Column(Integer, default=0)
    
    # Metadata
    generated_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    pdf_url = Column(String(500), nullable=True)
    status = Column(String(20), default="active")  # active, expired, revoked
    
    # Datos de validación pública
    verification_data = Column(JSON, default=dict)


# ============================================================================
# PAYMENTS: Registro manual de pagos por transferencia/deposito
# ============================================================================

class PaymentManual(Base):
    """
    Registro de pagos manuales recibidos por transferencia, depósito, Yape, etc.
    Administrado por el equipo de Conflict Zero (no es un gateway automático).
    """
    __tablename__ = "payments_manual"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    # Datos del pago
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="PEN")  # PEN, USD
    method = Column(String(20), nullable=False)  # transferencia, deposito, yape, plin, efectivo
    reference = Column(String(100), nullable=False)  # Número de operación, código de referencia
    payment_date = Column(String(10), nullable=True)  # YYYY-MM-DD
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_by = Column(String(50), default="admin")  # Quién registró el pago
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación (opcional)
    # user = relationship("User", back_populates="payments")

