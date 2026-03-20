# Conflict Zero

A modern web application built with FastAPI and Next.js.

## Project Structure

```
conflict-zero/
├── backend/              # FastAPI backend
│   ├── app/             # Application code
│   ├── tests/           # Test files
│   ├── Dockerfile       # Backend container
│   └── pyproject.toml   # Python dependencies
├── frontend/            # Next.js frontend
│   ├── app/             # Next.js app directory
│   ├── components/      # React components
│   ├── tests/           # Test files
│   ├── Dockerfile       # Frontend container
│   └── package.json     # Node dependencies
├── infrastructure/      # Docker Compose and infrastructure
│   ├── docker-compose.yml
│   ├── nginx/           # Nginx configuration
│   └── README.md
├── Makefile            # Common commands
└── .env.example        # Environment template
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for convenience commands)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd conflict-zero
cp .env.example .env
# Edit .env with your settings
```

### 2. Start Services

Using Make:
```bash
make setup    # Initial setup
make up       # Start all services
```

Or using Docker Compose directly:
```bash
cd infrastructure
docker-compose up -d
```

### 3. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Development

### Available Make Commands

```bash
make help              # Show all available commands
make build             # Build Docker images
make up                # Start services
make down              # Stop services
make logs              # View logs
make migrate           # Run database migrations
make test-backend      # Run backend tests
make test-frontend     # Run frontend tests
make lint-backend      # Run backend linters
make lint-frontend     # Run frontend linters
make shell-backend     # Open backend shell
make shell-frontend    # Open frontend shell
```

### Backend Development

The backend is built with FastAPI and includes:
- Async SQLAlchemy with PostgreSQL
- Redis caching
- JWT authentication
- Alembic migrations
- Comprehensive test suite

```bash
# Run migrations
make migrate

# Create a new migration
make migrate-create msg="add users table"

# Run tests
make test-backend

# Access PostgreSQL
make psql
```

### Frontend Development

The frontend is built with Next.js 14 and includes:
- App Router
- TypeScript
- Tailwind CSS
- React Query
- Zustand state management
- NextAuth.js authentication

```bash
# Run linter
make lint-frontend

# Run tests
make test-frontend
```

## Production Deployment

### Using Docker Compose

```bash
# Production mode with Nginx
make up-prod

# Or manually:
BACKEND_BUILD_TARGET=production \
FRONTEND_BUILD_TARGET=production \
docker-compose --profile nginx up -d
```

### Environment Variables

Key variables to set for production:

```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<generate-strong-secret>
NEXTAUTH_SECRET=<generate-strong-secret>
POSTGRES_PASSWORD=<strong-db-password>
REDIS_PASSWORD=<strong-redis-password>
```

Generate secrets:
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

## Architecture

### Services

| Service | Technology | Purpose |
|---------|------------|---------|
| Frontend | Next.js 14 | React SSR/SSG application |
| Backend | FastAPI | Python async API |
| Database | PostgreSQL 15 | Primary data store |
| Cache | Redis 7 | Caching & sessions |
| Proxy | Nginx | Reverse proxy & SSL |

### Network

All services communicate via Docker network `conflict-zero-network`.

### Volumes

- `postgres_data` - Persistent database storage
- `redis_data` - Redis persistence
- `backend_logs` - Application logs
- `nginx_logs` - Access/error logs

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linters
4. Submit a pull request

## License

[Your License Here]
