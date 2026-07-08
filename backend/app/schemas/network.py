"""
Esquemas para el feature "Mi Red" (Supplier Watchlist)
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class SupplierWatchlistCreate(BaseModel):
    """Schema para agregar un proveedor a la red"""
    supplier_ruc: str = Field(..., min_length=11, max_length=11, pattern=r"^\d{11}$")
    supplier_name: Optional[str] = Field(None, max_length=255)
    alias: Optional[str] = Field(None, max_length=100, description="Nombre personalizado para el proveedor")
    notes: Optional[str] = Field(None, max_length=1000)
    tags: Optional[List[str]] = Field(default_factory=list, description="Etiquetas para organizar proveedores")


class SupplierWatchlistBase(BaseModel):
    """Schema base para watchlist"""
    id: str
    user_id: str
    supplier_ruc: str
    supplier_name: Optional[str] = None
    alias: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None


class SupplierWatchlistResponse(SupplierWatchlistBase):
    """Schema completo de respuesta para un proveedor en la red"""
    current_status: Optional[Dict[str, Any]] = None
    current_score: Optional[int] = None
    has_pending_alerts: bool = False


class SupplierAlertResponse(BaseModel):
    """Schema para alertas de proveedores"""
    id: str
    user_id: str
    supplier_ruc: str
    supplier_name: Optional[str] = None
    change_type: str
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    severity: str = "medium"  # low, medium, high, critical
    is_read: bool = False
    email_sent: bool = False
    email_sent_at: Optional[datetime] = None
    created_at: datetime


class SupplierAlertUpdate(BaseModel):
    """Schema para actualizar una alerta"""
    is_read: bool


class NetworkStatsResponse(BaseModel):
    """Estadísticas de la red del usuario"""
    total_suppliers: int
    limit: int
    unread_alerts: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class NetworkSummaryResponse(BaseModel):
    """Resumen de la red para dashboard"""
    total_suppliers: int
    suppliers_added_this_month: int
    unread_alerts: int
    high_risk_suppliers: int
    recent_activity: List[Dict[str, Any]]
