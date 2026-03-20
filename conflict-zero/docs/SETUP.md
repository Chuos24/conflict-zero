# Conflict Zero - Guía de Configuración

## Requisitos

- Docker y Docker Compose
- Python 3.11+ (para desarrollo local sin Docker)
- Node.js 18+ (para desarrollo frontend)
- Cuenta en Decolecta API (opcional, tiene mock data)

## Inicio Rápido (Docker)

```bash
# 1. Clonar el repositorio
cd conflict-zero

# 2. Configurar variables de entorno
cp backend/.env.example backend/.env
# Editar backend/.env con tus credenciales

# 3. Iniciar todos los servicios
cd infrastructure
docker-compose up -d

# 4. Verificar estado
docker-compose ps
```

Servicios disponibles:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- PostgreSQL: localhost:5432
- Redis: localhost:6379

## Desarrollo Local (Sin Docker)

### Backend

```bash
cd backend

# Crear virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env

# Crear base de datos
sudo -u postgres createdb conflictzero

# Ejecutar migraciones
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Iniciar servidor de desarrollo
npm run dev
```

## Configuración de APIs Externas

### Decolecta API (Recomendado)

1. Registrarse en https://decolecta.com
2. Obtener API Key
3. Configurar en `backend/.env`:
   ```
   DECOLECTA_API_KEY=tu-api-key
   DECOLECTA_BASE_URL=https://api.decolecta.com/v1
   ```

Sin API key, el sistema usa datos simulados para desarrollo.

## Estructura del Proyecto

```
conflict-zero/
├── backend/              # FastAPI Application
│   ├── app/
│   │   ├── core/         # Config, seguridad, database
│   │   ├── models/       # SQLAlchemy models
│   │   ├── routers/      # API endpoints
│   │   ├── schemas/      # Pydantic schemas
│   │   └── services/     # Business logic
│   ├── alembic/          # Database migrations
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/             # Next.js Application
│   ├── app/              # App Router (Next.js 14)
│   ├── components/       # React components
│   ├── lib/              # Utilities, API client
│   ├── Dockerfile
│   └── package.json
├── infrastructure/       # Docker, AWS scripts
│   ├── docker-compose.yml
│   ├── docker-compose.prod.yml
│   └── aws-deploy/
└── docs/                 # Documentation
```

## Algoritmo de Scoring

El score (0-100) se calcula así:

| Factor | Peso | Descripción |
|--------|------|-------------|
| SUNAT | 30% | Deuda tributaria (escala logarítmica) |
| OSCE | 40% | Sanciones e inhabilitaciones |
| ML | 30% | Análisis predictivo de anomalías |

### Niveles de Riesgo

- **80-100**: Riesgo Bajo (Verde)
- **60-79**: Riesgo Moderado (Amarillo)
- **40-59**: Riesgo Alto (Naranja)
- **0-39**: Riesgo Crítico (Rojo)

## Endpoints API Principales

### Autenticación
- `POST /api/v1/auth/register` - Registro de usuario
- `POST /api/v1/auth/login` - Inicio de sesión
- `GET /api/v1/auth/me` - Perfil de usuario

### Verificación
- `POST /api/v1/verify/` - Verificar RUC (autenticado)
- `POST /api/v1/verify/public` - Verificar RUC (demo)
- `GET /api/v1/verify/history` - Historial de verificaciones

### Dashboard
- `GET /api/v1/dashboard/stats` - Estadísticas
- `GET /api/v1/dashboard/usage` - Uso del plan

## Despliegue en AWS

### Usando EC2

1. Crear instancia EC2 (t3.medium recomendado)
2. Configurar Security Group (puertos 22, 80, 443, 8000)
3. Conectar y ejecutar:

```bash
# Copiar user-data.sh a la instancia
scp infrastructure/aws-deploy/user-data.sh ec2-user@tu-ip:
ssh ec2-user@tu-ip
chmod +x user-data.sh
sudo ./user-data.sh
```

### Configurar SSL (Let's Encrypt)

```bash
sudo certbot --nginx -d api.tudominio.com
```

## Troubleshooting

### Error de conexión a PostgreSQL
```bash
# Verificar que PostgreSQL está corriendo
docker-compose logs db

# Resetear base de datos (CUIDADO: borra datos)
docker-compose down -v
docker-compose up -d
```

### Error de permisos
```bash
# Fix permissions en Linux/Mac
sudo chown -R $USER:$USER .
```

### Limpiar caché
```bash
# Redis
docker-compose exec redis redis-cli FLUSHALL
```

## Soporte

Para soporte técnico o preguntas:
- Email: soporte@czperu.com
- Dashboard: https://app.czperu.com

---
© 2026 Conflict Zero S.A.C. - Todos los derechos reservados.
