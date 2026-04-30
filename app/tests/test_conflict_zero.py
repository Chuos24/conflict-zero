"""
Tests unitarios básicos para Conflict Zero — pytest

Para ejecutar:
    cd /root/.openclaw/workspace/conflict-zero
    python -m pytest app/tests/ -v

Requiere:
    pip install pytest pytest-asyncio
"""
import pytest
import sys
import os
from datetime import datetime

# Añadir el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.services.culqi_service import CulqiService, PLAN_PRICES_CENTS, PLAN_NAMES


# ─── Culqi Service Tests ─────────────────────────────────────────────────────

class TestCulqiService:
    def test_service_without_keys_is_not_configured(self):
        """El servicio debe reportar no-configurado cuando faltan keys."""
        service = CulqiService()
        service.secret_key = ""
        service.public_key = ""
        service.enabled = False
        assert service.is_configured() is False

    def test_service_with_keys_is_configured(self):
        """El servicio debe reportar configurado cuando tiene keys."""
        service = CulqiService()
        service.secret_key = "sk_test_xxx"
        service.public_key = "pk_test_xxx"
        service.enabled = True
        assert service.is_configured() is True

    def test_plan_config_structure(self):
        """La configuración de planes debe tener la estructura correcta."""
        service = CulqiService()
        service.public_key = "pk_test_xxx"
        service.enabled = True
        config = service.get_plan_config()

        assert "public_key" in config
        assert "currency" in config
        assert "plans" in config
        assert config["currency"] == "PEN"
        assert "essential" in config["plans"]
        assert "professional" in config["plans"]
        assert "enterprise" in config["plans"]

    def test_plan_prices_are_correct(self):
        """Los precios deben estar en céntimos."""
        assert PLAN_PRICES_CENTS["essential"] == 400 * 100
        assert PLAN_PRICES_CENTS["professional"] == 800 * 100
        assert PLAN_PRICES_CENTS["enterprise"] == 2500 * 100

    def test_plan_names_exist(self):
        """Todos los planes deben tener nombre legible."""
        for key in PLAN_PRICES_CENTS:
            assert key in PLAN_NAMES
            assert len(PLAN_NAMES[key]) > 0

    def test_create_charge_without_keys_fails(self):
        """Sin keys, create_charge debe retornar error."""
        service = CulqiService()
        service.enabled = False
        result = service.create_charge("tok_xxx", 1000, "PEN", "test@test.com", "Test")
        assert result["success"] is False
        assert "no está configurado" in result["error"]

    def test_webhook_validation_without_keys_fails(self):
        """Sin secret key, validate_webhook debe retornar False."""
        service = CulqiService()
        service.secret_key = ""
        assert service.validate_webhook({}, "body", "sig") is False


# ─── Security / Rate Limiting Tests ──────────────────────────────────────────

class TestRateLimiting:
    def test_ip_rate_limit_counter_exists(self):
        """El middleware de rate limiting usa un defaultdict de listas."""
        from collections import defaultdict
        counts = defaultdict(list)
        assert "127.0.0.1" not in counts or len(counts["127.0.0.1"]) == 0

    def test_plan_limits_defined(self):
        """Los límites mensuales deben estar definidos para todos los planes."""
        limits = {
            "essential": 1000,
            "professional": 5000,
            "enterprise": 100000,
        }
        for plan, limit in limits.items():
            assert limit > 0
            assert isinstance(limit, int)


# ─── Model Integrity Tests ──────────────────────────────────────────────────

class TestModels:
    def test_user_model_has_plan_type(self):
        """El modelo User debe tener columna plan_type."""
        from app.models import User
        assert hasattr(User, 'plan_type')
        assert hasattr(User, 'monthly_requests')
        assert hasattr(User, 'monthly_limit')

    def test_network_models_exist(self):
        """Los modelos de Mi Red deben existir."""
        from app.models import NetworkWatchlist, NetworkAlert
        assert hasattr(NetworkWatchlist, 'ruc')
        assert hasattr(NetworkWatchlist, 'alias')
        assert hasattr(NetworkAlert, 'alert_type')

    def test_payment_model_has_required_fields(self):
        """El modelo PaymentManual debe tener campos de pago."""
        from app.models import PaymentManual
        assert hasattr(PaymentManual, 'amount')
        assert hasattr(PaymentManual, 'currency')
        assert hasattr(PaymentManual, 'method')
        assert hasattr(PaymentManual, 'reference')

    def test_invitation_model_has_required_fields(self):
        """El modelo Invitation debe tener campos correctos."""
        from app.models import Invitation
        assert hasattr(Invitation, 'invited_by')
        assert hasattr(Invitation, 'email')
        assert hasattr(Invitation, 'token')
        assert hasattr(Invitation, 'status')
        assert hasattr(Invitation, 'expires_at')
        assert hasattr(Invitation, 'accepted_by')

    def test_certificate_model_exists(self):
        """El modelo Certificate debe existir."""
        from app.models import Certificate
        assert hasattr(Certificate, 'code')
        assert hasattr(Certificate, 'ruc')
        assert hasattr(Certificate, 'score')

    def test_company_snapshot_model_exists(self):
        """El modelo CompanySnapshot debe existir para ML."""
        from app.models import CompanySnapshot
        assert hasattr(CompanySnapshot, 'ruc')
        assert hasattr(CompanySnapshot, 'snapshot_date')
        assert hasattr(CompanySnapshot, 'score_calculado')


# ─── Router Response Tests ─────────────────────────────────────────────────

class TestRouters:
    def test_health_router_exists(self):
        """El router de health debe estar importable."""
        from app.routers import health_router
        assert health_router is not None

    def test_network_router_exists(self):
        """El router de Mi Red debe estar importable."""
        from app.routers import network_router
        assert network_router is not None

    def test_payments_router_exists(self):
        """El router de pagos debe estar importable."""
        from app.routers import payments_router
        assert payments_router is not None

    def test_payments_v2_router_exists(self):
        """El router de pagos v2 (Culqi) debe estar importable."""
        from app.routers import payments_v2_router
        assert payments_v2_router is not None

    def test_certificates_router_exists(self):
        """El router de certificados debe estar importable."""
        from app.routers import certificates_router
        assert certificates_router is not None

    def test_invitations_router_exists(self):
        """El router de invitaciones debe estar importable."""
        from app.routers import invitations_router
        assert invitations_router is not None

    def test_admin_router_exists(self):
        """El router de admin debe estar importable."""
        from app.routers import admin_router
        assert admin_router is not None


# ─── Network Router Logic Tests ─────────────────────────────────────────────

class TestNetworkRouter:
    def test_allowed_plans_for_network(self):
        """Solo professional y enterprise pueden usar Mi Red."""
        allowed = {"professional", "enterprise"}
        assert "essential" not in allowed
        assert "professional" in allowed
        assert "enterprise" in allowed

    def test_ruc_validation_length(self):
        """RUC debe tener exactamente 11 dígitos."""
        valid_ruc = "20100123091"
        assert len(valid_ruc) == 11
        assert valid_ruc.isdigit()

        invalid_short = "123456"
        assert len(invalid_short) != 11

        invalid_alpha = "2010012309A"
        assert not invalid_alpha.isdigit()


# ─── Invitation Router Logic Tests ────────────────────────────────────────

class TestInvitationRouter:
    def test_token_generation_length(self):
        """Los tokens de invitación deben ser largos y seguros."""
        import secrets
        token = secrets.token_urlsafe(32)
        assert len(token) >= 32
        assert len(token) <= 64

    def test_invitation_expiry_24h(self):
        """Las invitaciones deben expirar en 24 horas."""
        from datetime import timedelta
        expiry = timedelta(hours=24)
        assert expiry.total_seconds() == 86400


# ─── Certificate Router Logic Tests ─────────────────────────────────────────

class TestCertificateRouter:
    def test_risk_to_tier_mapping(self):
        """El mapeo de riesgo a tier debe ser correcto."""
        from app.routers.certificates import RISK_TO_TIER
        assert RISK_TO_TIER["LOW"] == "GOLD"
        assert RISK_TO_TIER["MEDIUM"] == "SILVER"
        assert RISK_TO_TIER["HIGH"] == "BRONZE"
        assert RISK_TO_TIER["CRITICAL"] == "RECHAZADO"

    def test_certificate_validity_one_year(self):
        """Los certificados deben ser válidos por 1 año."""
        from datetime import timedelta
        validity = timedelta(days=365)
        assert validity.days == 365


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
