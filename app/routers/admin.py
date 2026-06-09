"""
Admin Router - Payment System + Plan Activation
Endpoints para gestión de pagos manuales y activación de planes
"""

from fastapi import APIRouter, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import os
import jwt

# Database
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models import User
from app.core.security import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin"])

# Config
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN', 'CZ2026ADM')
JWT_SECRET = os.environ.get('JWT_SECRET', 'conflict-zero-secret-key-2024')


# ============ PYDANTIC MODELS ============
