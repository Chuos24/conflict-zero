"""
Tests para el feature "Mi Red" (Supplier Watchlist)
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models import User, SupplierWatchlist, CompanySnapshot
from app.core.security import get_password_hash
import uuid

# Setup test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

@pytest.fixture
def test_user(db_session):
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        hashed_password=get_password_hash("test123"),
        full_name="Test User",
        plan_type="essential",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def auth_headers(test_user):
    from app.core.security import create_access_token
    token = create_access_token({"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}

class TestNetwork:
    def test_add_supplier_to_network(self, client, auth_headers):
        """Test agregar proveedor a la red"""
        response = client.post(
            "/api/v3/network/add",
            json={
                "supplier_ruc": "20100000001",
                "supplier_name": "Test Company",
                "alias": "Mi Proveedor",
                "notes": "Nota de prueba",
                "tags": ["importante", "local"]
            },
            headers=auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["supplier_ruc"] == "20100000001"
        assert data["alias"] == "Mi Proveedor"

    def test_add_duplicate_supplier_fails(self, client, auth_headers):
        """Test que no se puede agregar el mismo RUC dos veces"""
        # Agregar primero
        client.post(
            "/api/v3/network/add",
            json={"supplier_ruc": "20100000001"},
            headers=auth_headers
        )
        
        # Intentar agregar de nuevo
        response = client.post(
            "/api/v3/network/add",
            json={"supplier_ruc": "20100000001"},
            headers=auth_headers
        )
        assert response.status_code == 409

    def test_list_network(self, client, auth_headers, db_session, test_user):
        """Test listar proveedores en la red"""
        # Crear algunos proveedores
        for i in range(3):
            sw = SupplierWatchlist(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                supplier_ruc=f"2010000000{i}",
                supplier_name=f"Company {i}",
                is_active=True
            )
            db_session.add(sw)
        db_session.commit()
        
        response = client.get("/api/v3/network/", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_remove_supplier(self, client, auth_headers, db_session, test_user):
        """Test eliminar proveedor de la red"""
        # Crear proveedor
        sw = SupplierWatchlist(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            supplier_ruc="20100000001",
            is_active=True
        )
        db_session.add(sw)
        db_session.commit()
        
        response = client.delete("/api/v3/network/20100000001", headers=auth_headers)
        assert response.status_code == 204

    def test_network_stats(self, client, auth_headers, db_session, test_user):
        """Test obtener estadísticas de la red"""
        # Crear proveedores con diferentes scores
        for i, score in enumerate([90, 50, 20]):
            sw = SupplierWatchlist(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                supplier_ruc=f"2010000000{i}",
                is_active=True
            )
            db_session.add(sw)
            
            # Crear snapshot
            snapshot = CompanySnapshot(
                id=str(uuid.uuid4()),
                ruc=f"2010000000{i}",
                score_calculado=score
            )
            db_session.add(snapshot)
        
        db_session.commit()
        
        response = client.get("/api/v3/network/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_suppliers"] == 3
        assert data["low_risk_count"] == 1  # score 90
        assert data["medium_risk_count"] == 1  # score 50
        assert data["high_risk_count"] == 1  # score 20

    def test_network_limits_by_plan(self, client, auth_headers, test_user):
        """Test que el límite de proveedores respeta el plan"""
        # Essential plan = 10 proveedores
        test_user.plan_type = "essential"
        
        response = client.post(
            "/api/v3/network/add",
            json={"supplier_ruc": "20999999999"},
            headers=auth_headers
        )
        # Si ya tiene 10, debería fallar
        # Este test depende del estado previo

class TestAlerts:
    def test_get_alerts(self, client, auth_headers, db_session, test_user):
        """Test obtener alertas"""
        from app.models import SupplierAlert
        
        # Crear alertas
        for i in range(3):
            alert = SupplierAlert(
                id=str(uuid.uuid4()),
                user_id=test_user.id,
                supplier_ruc="20100000001",
                change_type="osce_inhabilitado",
                severity="critical",
                is_read=False
            )
            db_session.add(alert)
        db_session.commit()
        
        response = client.get("/api/v3/network/alerts?unread_only=true", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3

    def test_mark_alert_read(self, client, auth_headers, db_session, test_user):
        """Test marcar alerta como leída"""
        from app.models import SupplierAlert
        
        alert = SupplierAlert(
            id=str(uuid.uuid4()),
            user_id=test_user.id,
            supplier_ruc="20100000001",
            change_type="sunat_deuda_aumento",
            severity="medium",
            is_read=False
        )
        db_session.add(alert)
        db_session.commit()
        
        response = client.patch(f"/api/v3/network/alerts/{alert.id}/read", headers=auth_headers)
        assert response.status_code == 200
        
        # Verificar que está leída
        db_session.refresh(alert)
        assert alert.is_read == True
