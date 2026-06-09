#!/usr/bin/env python3
"""
ConflictZero FastAPI Application - Production Ready
Minimal, robust entry point that works reliably
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

# Create app
app = FastAPI(
    title="ConflictZero API",
    description="Corporate conflict-of-interest and supplier risk verification",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.get("/")
async def root():
    return {"message": "ConflictZero API v1.0.0"}

@app.get("/api/v1/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}

@app.on_event("startup")
async def startup():
    print("✅ ConflictZero API startup")

@app.on_event("shutdown")
async def shutdown():
    print("✅ ConflictZero API shutdown")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)