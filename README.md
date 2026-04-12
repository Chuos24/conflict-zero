# 🏛️ Conflict Zero

**Verificación predictiva de riesgos para RUCs peruanos**

Plataforma UHNW (Ultra High Net Worth) para evaluar riesgo de contratación pública mediante análisis de datos SUNAT, OSCE y TCE.

## 🎨 Características

- ✅ **Datos Reales**: Conexión directa con SUNAT vía Perú API
- ✅ **Scoring 0-100**: Algoritmo ponderado de riesgo
- ✅ **Diseño Premium**: Dark theme + acentos dorados
- ✅ **Planes de Pago**: Essential, Professional, Enterprise
- ✅ **API REST**: Documentada con Swagger/OpenAPI

## 📁 Estructura

```
conflict-zero/
├── backend/          # FastAPI + PostgreSQL
│   ├── app/          # Código fuente
│   ├── render.yaml   # Configuración Render
│   └── requirements.txt
│
└── frontend/         # Next.js 14
    ├── app/          # Páginas
    ├── components/   # Componentes React
    └── out/          # Build estático (Netlify)
```

## 🚀 Deploy

### Backend (Render)

1. Fork este repositorio a tu cuenta `Chuos24`
2. Ve a [render.com](https://render.com)
3. Click "New Web Service" → Conecta tu repo
4. Render detectará automáticamente `render.yaml`
5. Agrega tu `PERU_API_KEY` en Environment Variables
6. Deploy!

### Frontend (Netlify)

1. Descarga `frontend/conflict-zero-static.zip`
2. Ve a [netlify.com](https://netlify.com)
3. Arrastra el ZIP (deploy estático)
4. Configura la URL del backend en Site Settings → Environment Variables

## 🛠️ Desarrollo Local

### Backend
```bash
cd backend
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## 📝 REGLA DE DESARROLLO

> **⚠️ IMPORTANTE: Convenciones de código para el equipo**

- **Render corre**: `app.main:app` (routers modulares)
- **NO modificar** `api_v3.py` para features nuevos
- **Nuevos endpoints** van en `app/routers/`
- **Claude Code** escribe en tu Mac → push → Render autodeploya

### Arquitectura
```
app/
├── main.py           # Entry point (Render lo ejecuta)
├── routers/          # Endpoints modulares (USAR ESTO)
│   ├── auth.py
│   ├── admin.py      # <-- Nuevos endpoints admin aquí
│   └── ...
└── models/           # SQLAlchemy models

api_v3.py            # ⚠️ LEGACY - No modificar
```

## 📄 Licencia

Copyright © 2025 Conflict Zero. Todos los derechos reservados.
