# Architecture Decision Record: Conflict Zero Platform

## Overview
Integrating existing static HTML frontend (czperu.com) with new full-stack SaaS platform.

## Existing Assets
- Landing page: Elegant dark/gold theme, Calendly integration
- Certificate verification system (verificar.html)
- Admin panel with basic auth (administrativo.html)
- AWS Lambda API for OSCE/TCE/SUNAT queries

## New Components

### Backend (FastAPI + PostgreSQL + Redis)
- Custom scoring algorithm (0-100)
- JWT authentication
- API rate limiting
- Verification history tracking
- PDF report generation

### Frontend (Next.js)
- Dashboard with real-time verification
- User management
- Subscription billing
- API key management

## Data Flow
```
User → Next.js Frontend → FastAPI Backend → Decolecta API (SUNAT/OSCE/TCE)
                                    ↓
                              PostgreSQL (history)
                                    ↓
                              Redis (cache)
```

## Deployment
- AWS EC2 (backend)
- Vercel (frontend)
- RDS PostgreSQL
- ElastiCache Redis

## Integration Strategy
1. Keep existing landing page as-is (marketing site)
2. New /app subdomain for SaaS dashboard
3. API endpoints power both old certificate viewer and new dashboard
4. Gradual migration of users from static admin panel to full dashboard
