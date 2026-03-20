# Conflict Zero - Plataforma de Verificación Predictiva de Riesgo Contractual

SaaS B2B para reducir el proceso de due diligence de 3 horas a 30 segundos mediante análisis automatizado de RUCs peruanos.

## 🚀 Stack Tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Frontend | Next.js + React | 14.0.3 |
| Backend | Python FastAPI | 0.104.1 |
| Database | PostgreSQL | 15.3 |
| Caché | Redis | 7.0 |
| Hosting | AWS EC2 | t3.medium |

## 📁 Estructura del Proyecto

```
conflict-zero/
├── backend/          # API FastAPI
├── frontend/         # Next.js 14 App Router
├── infrastructure/   # Docker, Terraform, Scripts AWS
└── docs/            # Documentación técnica
```

## 🛠️ Instalación Local

### Requisitos Previos
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Docker (Todo en uno)

```bash
cd infrastructure
docker-compose up -d
```

## 🔑 Variables de Entorno

### Backend (.env)
```env
# Database
DATABASE_URL=postgresql://user:pass@localhost/conflictzero

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# APIs Externas
DECOLECTA_API_KEY=your-api-key
DECOLECTA_BASE_URL=https://api.decolecta.com/v1

# AWS (opcional para local)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
```

## 📊 Algoritmo de Scoring

El motor calcula una puntuación 0-100 basada en:

| Factor | Peso | Descripción |
|--------|------|-------------|
| Deuda SUNAT | 30% | Escala logarítmica para normalizar montos |
| Sanciones OSCE | 40% | Indicador binario crítico |
| Patrones Predictivos | 30% | ML para detección de anomalías |

## 📚 Documentación API

Una vez iniciado el backend, visita:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🏗️ Despliegue AWS

Ver `infrastructure/aws-deploy/` para scripts de despliegue automatizado.

## 📄 Licencia

© 2026 Conflict Zero S.A.C. - Todos los derechos reservados.
