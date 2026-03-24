from app.routers.auth import router as auth_router
from app.routers.verification import router as verification_router
from app.routers.dashboard import router as dashboard_router
from app.routers.health import router as health_router
from app.routers.consulta import router as consulta_router

__all__ = ["auth_router", "verification_router", "dashboard_router", "health_router", "consulta_router"]
