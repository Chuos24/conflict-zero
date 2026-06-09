from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_password, create_access_token, get_password_hash, get_current_active_user
)
from app.models import User
from app.schemas import Token, UserCreate, UserResponse, LoginRequest, UserUpdate, ApiKeyRegenerateResponse
from app.services.email import get_email_service
from pydantic import BaseModel, EmailStr, Field

import os
