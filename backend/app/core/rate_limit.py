from fastapi import Request, HTTPException, status
from typing import Dict, Optional
import time
from collections import defaultdict

# Simple in-memory rate limiter (use Redis in production)
class RateLimiter:
    def __init__(self):
        # requests_store: {user_id: [(timestamp, count)]}
        self.requests_store: Dict[str, list] = defaultdict(list)
        self.window_seconds = 60  # 1 minute window
    
    def _clean_old_requests(self, user_id: str):
        """Remove requests outside the time window"""
        now = time.time()
        cutoff = now - self.window_seconds
        self.requests_store[user_id] = [
            req for req in self.requests_store[user_id] 
            if req > cutoff
        ]
    
    def is_allowed(self, user_id: str, limit: int) -> bool:
        """Check if user has not exceeded their rate limit"""
        self._clean_old_requests(user_id)
        current_count = len(self.requests_store[user_id])
        return current_count < limit
    
    def record_request(self, user_id: str):
        """Record a new request timestamp"""
        self.requests_store[user_id].append(time.time())

# Plan-based rate limits (requests per minute)
PLAN_RATE_LIMITS = {
    "red": 10,           # 10 req/min
    "essential": 30,     # 30 req/min
    "professional": 60,  # 60 req/min
    "enterprise": 120,   # 120 req/min
}

limiter = RateLimiter()

def get_rate_limit_for_user(plan_type: str) -> int:
    """Get the rate limit for a specific plan"""
    return PLAN_RATE_LIMITS.get(plan_type.lower(), 30)

def check_rate_limit(request: Request, user_id: str, plan_type: str):
    """
    Check if the user has exceeded their rate limit.
    Raises HTTPException if limit exceeded.
    """
    limit = get_rate_limit_for_user(plan_type)
    
    if not limiter.is_allowed(user_id, limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Limit: {limit} requests per minute for your plan ({plan_type}).",
            headers={"Retry-After": str(limiter.window_seconds)}
        )
    
    limiter.record_request(user_id)
    
    # Add rate limit headers to response (set in endpoint via response.headers)
    return {
        "X-RateLimit-Limit": str(limit),
        "X-RateLimit-Remaining": str(limit - len(limiter.requests_store[user_id])),
    }
