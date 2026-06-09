"""
app/core/middleware.py
Security Headers + Rate Limiting Middleware
"""

from fastapi.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

# ============ RATE LIMITER ============
limiter = Limiter(key_func=get_remote_address)

def rate_limit_error_handler(request: Request, exc: RateLimitExceeded):
    """Handle rate limit exceeded errors"""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "error": "rate_limit_exceeded"
        }
    )

# ============ SECURITY HEADERS MIDDLEWARE ============
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Content Security Policy (strict)
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # HSTS (force HTTPS for 1 year)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        # Permissions Policy*        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Remove Server header (don't leak info)
        response.headers.pop("Server", None)
        
        logger.debug(f"Security headers added to {request.url.path}")
        return response
