from pydantic import BaseModel, EmailStr, Field, validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# ============== User Schemas ==============

class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    company_name: Optional[str] = Field(None, max_length=255)
    ruc: Optional[str] = Field(None, min_length=11, max_length=11)

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    company_name: Optional[str] = None
    ruc: Optional[str] = Field(None, min_length=11, max_length=11)
    current_password: Optional[str] = Field(None, min_length=8)
    new_password: Optional[str] = Field(None, min_length=8)

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    plan_type: str
    monthly_requests: int
    monthly_limit: int
    is_admin: bool = False
    plan: Optional[str] = None
    plan_activated_at: Optional[datetime] = None
    plan_expires_at: Optional[datetime] = None
    api_key: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

# ============== Auth Schemas ==============

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[datetime] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

# ============== Verification Schemas ==============

class VerificationRequest(BaseModel):
    ruc: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    
class SunatData(BaseModel):
    debt_amount: float
    tax_status: str
    contributor_status: Optional[str] = None
    address: Optional[str] = None
    department: Optional[str] = None
    province: Optional[str] = None
    district: Optional[str] = None
    ubigeo: Optional[str] = None
    data_source: Optional[str] = None
    last_updated: Optional[datetime] = None

class OsceSanction(BaseModel):
    sanction_id: str
    description: str
    date: Optional[str] = None  # Accept date strings like '2021-12-29'
    status: str
    entity: str

class TceSanction(BaseModel):
    sanction_id: str
    description: str
    date: Optional[str] = None  # Accept date strings
    status: str
    type: str

class MLAnalysis(BaseModel):
    anomaly_score: float
    risk_factors: List[str]
    confidence: float

class ScoreBreakdown(BaseModel):
    sunat_contribution: float
    osce_contribution: float
    tce_contribution: float
    ml_contribution: float
    total_score: int

class VerificationResponse(BaseModel):
    id: Optional[UUID] = None
    ruc: str
    company_name: Optional[str] = None
    score: int = Field(..., ge=0, le=100)
    risk_level: str  # low, medium, high, critical
    
    # Detailles
    sunat_data: SunatData
    osce_sanctions: List[OsceSanction]
    tce_sanctions: List[TceSanction]
    ml_analysis: MLAnalysis
    score_breakdown: ScoreBreakdown
    
    # Metadata
    verification_date: datetime
    pdf_url: Optional[str] = None
    cached: bool = False
    
    model_config = ConfigDict(from_attributes=True)

class VerificationHistory(BaseModel):
    id: UUID
    ruc: str
    company_name: Optional[str] = None
    score: int
    risk_level: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

# ============== API Key Schemas ==============

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)

class ApiKeyResponse(BaseModel):
    id: UUID
    name: str
    key: str  # Only shown once on creation
    is_active: bool
    usage_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class ApiKeyListItem(BaseModel):
    id: UUID
    name: str
    is_active: bool
    last_used_at: Optional[datetime] = None
    usage_count: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class ApiKeyRegenerateResponse(BaseModel):
    api_key: str
    message: str

# ============== Dashboard Schemas ==============

class DashboardStats(BaseModel):
    total_verifications: int
    verifications_this_month: int
    average_score: float
    risk_distribution: Dict[str, int]  # low, medium, high, critical counts
    recent_verifications: List[VerificationHistory]

class HealthCheck(BaseModel):
    status: str
    version: str
    database: str
    redis: str
    timestamp: datetime