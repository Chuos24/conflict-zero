# Conflict Zero - Infrastructure

This directory contains Docker Compose configuration for local development and production deployment.

## Quick Start

1. **Copy environment variables:**
   ```bash
   cp ../.env.example ../.env
   # Edit .env with your settings
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **View logs:**
   ```bash
   docker-compose logs -f
   ```

4. **Run database migrations:**
   ```bash
   docker-compose --profile migrate run --rm migrate
   ```

## Services

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Primary database |
| Redis | 6379 | Caching & sessions |
| Backend | 8000 | FastAPI application |
| Frontend | 3000 | Next.js application |
| Nginx | 80/443 | Reverse proxy (optional) |

## Profiles

Use Docker Compose profiles to run specific configurations:

```bash
# Development (default)
docker-compose up -d

# With Nginx reverse proxy
docker-compose --profile nginx up -d

# Production mode (optimized builds)
BACKEND_BUILD_TARGET=production FRONTEND_BUILD_TARGET=production docker-compose up -d

# Run database migrations
docker-compose --profile migrate run --rm migrate
```

## Commands

```bash
# Build all images
docker-compose build

# Rebuild a specific service
docker-compose build backend

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ data loss)
docker-compose down -v

# View service logs
docker-compose logs -f [service]

# Execute command in container
docker-compose exec backend poetry run pytest
docker-compose exec frontend npm run lint

# Scale backend workers
docker-compose up -d --scale backend=3
```

## Network

All services communicate via the `conflict-zero-network` bridge network (172.25.0.0/16).

Service hostnames:
- `postgres` - PostgreSQL database
- `redis` - Redis cache
- `backend` - FastAPI backend
- `frontend` - Next.js frontend
- `nginx` - Nginx reverse proxy

## Volumes

| Volume | Purpose |
|--------|---------|
| `postgres_data` | Persistent database storage |
| `redis_data` | Redis persistence |
| `backend_logs` | Application logs |
| `nginx_logs` | Access/error logs |

## Health Checks

All services include health checks:
- PostgreSQL: `pg_isready`
- Redis: `redis-cli ping`
- Backend: HTTP GET `/health`
- Frontend: HTTP GET `/api/health`
- Nginx: HTTP GET `/health`

## Troubleshooting

### Port Conflicts

If ports are already in use, modify them in `.env`:
```bash
POSTGRES_PORT=5433
REDIS_PORT=6380
BACKEND_PORT=8001
FRONTEND_PORT=3001
```

### Database Connection Issues

Ensure the database is healthy before starting backend:
```bash
docker-compose up -d postgres redis
docker-compose logs -f postgres
# Wait for "database system is ready"
docker-compose up -d backend frontend
```

### Reset Everything

⚠️ **Warning: This will delete all data!**

```bash
docker-compose down -v
docker-compose up -d
```

## Production Deployment

1. Update `.env` with production values
2. Set `ENVIRONMENT=production`
3. Use `BACKEND_BUILD_TARGET=production`
4. Use `FRONTEND_BUILD_TARGET=production`
5. Enable Nginx profile: `--profile nginx`
6. Configure SSL certificates in `nginx/ssl/`
