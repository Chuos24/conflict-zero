from app.routers.auth import router as auth_router
from app.routers.verification import router as verification_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.consulta import router as consulta_router
from app.routers.debug import router as debug_router
from app.routers.compare import router as compare_router
from app.routers.payments import router as payments_router
from app.routers.admin import router as admin_router
from app.routers.notifications import router as notifications_router
from app.routers.payments_admin import router as payments_admin_router
from app.routers.invitations import router as invitations_router
from app.routers.certificates import router as certificates_router
from app.routers.network import router as network_router

__all__ = ["auth_router", "verification_router", "dashboard_router", "health_router", 
           "consulta_router", "debug_router", "compare_router", "payments_router", 
           "admin_router", "notifications_router", "payments_admin_router",
           "invitations_router", "certificates_router", "network_router"]
