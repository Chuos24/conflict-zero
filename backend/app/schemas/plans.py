from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ============== Plan Schemas ==============

class PlanBase(BaseModel):
    id: str
    name: str
    price: float
    monthly_limit: int
    features: List[str]
    highlighted: Optional[bool] = False

class PlanResponse(PlanBase):
    class Config:
        orm_mode = True

class PlansList(BaseModel):
    plans: List[PlanResponse]

# ============== Subscription Schemas ==============

class SubscriptionBase(BaseModel):
    user_id: UUID
    plan_id: str
    status: str = Field(..., regex="^(active|cancelled|past_due|paused)$")
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False

class SubscriptionCreate(BaseModel):
    plan_id: str
    payment_method_id: Optional[str] = None

class SubscriptionUpdate(BaseModel):
    plan_id: Optional[str] = None
    cancel_at_period_end: Optional[bool] = None

class SubscriptionResponse(SubscriptionBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# ============== Payment Schemas ==============

class PaymentBase(BaseModel):
    subscription_id: UUID
    amount: float
    currency: str = "PEN"
    status: str = Field(..., regex="^(pending|completed|failed|refunded)$")
    payment_method: str = Field(..., regex="^(stripe|culqi|yape|plin)$")
    provider_payment_id: Optional[str] = None

class PaymentCreate(BaseModel):
    subscription_id: UUID
    amount: float
    payment_method: str
    provider_payment_id: Optional[str] = None

class PaymentResponse(PaymentBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True

# ============== Webhook Schemas ==============

class WebhookPayload(BaseModel):
    event_type: str
    data: dict
    signature: Optional[str] = None

class WebhookResponse(BaseModel):
    status: str
    message: str
    event_id: Optional[str] = None

# ============== Compare Request Schemas ==============

class CompareRequest(BaseModel):
    rucs: List[str] = Field(..., min_items=2, max_items=10)
    
    @validator('rucs')
    def validate_rucs(cls, v):
        for ruc in v:
            if len(ruc) != 11 or not ruc.isdigit():
                raise ValueError(f"RUC {ruc} must be 11 digits")
        return v

class CompareResultItem(BaseModel):
    ruc: str
    company_name: Optional[str] = None
    score: int
    risk_level: str
    sunat_debt: float
    osce_sanctions_count: int
    tce_sanctions_count: int
    status: str

class CompareResponse(BaseModel):
    results: List[CompareResultItem]
    comparison_date: datetime
    average_score: float
    highest_risk: Optional[str] = None
    lowest_risk: Optional[str] = None

    class Config:
        orm_mode = True

# ============== System Log Schemas ==============

class SystemLogBase(BaseModel):
    level: str = Field(..., regex="^(debug|info|warning|error|critical)$")
    message: str
    source: Optional[str] = None
    meta_data: Optional[dict] = None

class SystemLogResponse(SystemLogBase):
    id: UUID
    created_at: datetime

    class Config:
        orm_mode = True

class SystemLogList(BaseModel):
    logs: List[SystemLogResponse]
    total: int
    page: int
    page_size: int
