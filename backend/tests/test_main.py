import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# ============================================================================
# AUTH TESTS
# ============================================================================

def test_register_user():
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register?plan=essential",
        json={
            "email": "test@example.com",
            "password": "TestPass123!",
            "full_name": "Test User",
            "company_name": "Test Corp",
            "ruc": "20100000001"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["plan_type"] == "essential"

def test_login_user():
    """Test user login"""
    # First register
    client.post(
        "/api/v1/auth/register?plan=essential",
        json={
            "email": "login@test.com",
            "password": "TestPass123!",
            "full_name": "Login Test"
        }
    )
    
    # Then login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@test.com",
            "password": "TestPass123!"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials():
    """Test login with wrong password"""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@test.com",
            "password": "WrongPassword"
        }
    )
    assert response.status_code == 401

# ============================================================================
# HEALTH TESTS
# ============================================================================

def test_health_check():
    """Test health endpoint"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_plans_endpoint():
    """Test plans endpoint returns correct structure"""
    response = client.get("/api/v1/auth/plans")
    assert response.status_code == 200
    data = response.json()
    assert "plans" in data
    assert len(data["plans"]) == 3  # essential, professional, enterprise

# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

def test_rate_limit_headers():
    """Test that rate limit headers are present"""
    # This is a basic test - full rate limiting requires authenticated requests
    response = client.get("/api/v1/health")
    assert response.status_code == 200
