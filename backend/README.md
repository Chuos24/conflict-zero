# Conflict Zero - Backend

API de verificación de RUC peruano con datos reales de SUNAT, OSCE y TCE.

## 🚀 Deploy Rápido a Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Chuos24/conflict-zero)

### Variables de Entorno Requeridas

```bash
# Database (Render la configura automáticamente)
DATABASE_URL=postgresql://...

# Seguridad
SECRET_KEY=tu-clave-secreta-aqui

# APIs Externas
PERU_API_KEY=tu-api-key-de-peruapi.com

# Configuración
ENVIRONMENT=production
ALLOWED_HOSTS=*
```

## 📦 Instalación Local

```bash
# 1. Clonar
git clone https://github.com/Chuos24/conflict-zero.git
cd conflict-zero/backend

# 2. Virtual env
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 5. Ejecutar
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 🔗 Endpoints

| Endpoint | Descripción |
|----------|-------------|
| `POST /api/v1/auth/register` | Registro de usuario |
| `POST /api/v1/auth/login` | Login (retorna JWT) |
| `POST /api/v1/verify/` | Verificar RUC (auth) |
| `POST /api/v1/verify/public` | Verificar RUC (público) |

## 👤 Usuario Founder (Acceso Ilimitado)

```
Email: founder@conflictzero.com
Password: FounderPass2025!
Plan: Enterprise (ilimitado)
```

## 📄 Licencia

Copyright © 2025 Conflict Zero. Todos los derechos reservados.
# Redeploy trigger Wed Mar 25 11:52:46 AM CST 2026
