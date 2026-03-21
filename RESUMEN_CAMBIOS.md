# Conflict Zero - Resumen de Cambios para Producción

## ✅ Estado: LISTO PARA DEPLOY

---

## 1. Datos Reales Garantizados

### Problema Anterior
- El sistema usaba datos simulados (mock) cuando no había API key configurada
- No había diferencia entre demo y producción

### Solución Implementada
- **Perú API** como fuente primaria de SUNAT (plan free: 100 consultas/día)
- **Decolecta API** como fallback opcional
- Si no hay APIs configuradas, el sistema retorna error 503 (no datos falsos)

### Archivos Modificados
- `aws/lambda/lambda_function_v6.py` - Lambda actualizado con Perú API
- `backend/app/services/external_api.py` - Servicio de APIs externas
- `backend/app/services/verification.py` - Verificación con datos reales
- `backend/app/core/config.py` - Configuración de PERUAPI_TOKEN

---

## 2. Planes Diferenciados

### Planes Disponibles
| Plan | Precio | Consultas | Features |
|------|--------|-----------|----------|
| Free | $0 | 100/mes | Datos reales, sanciones OSCE/TCE |
| Starter | $400 | 1,000/mes | + Certificados PDF, historial |
| Pro | $800 | 5,000/mes | + API access, bulk upload |
| Enterprise | $2,000 | ∞ | + SLA, soporte 24/7, webhooks |

### Archivos Creados/Modificados
- `frontend/app/pricing/page.tsx` - Página de pricing completa
- `frontend/app/register/page.tsx` - Registro con selección de plan
- `frontend/app/dashboard/layout.tsx` - Sidebar con info de plan y uso
- `backend/app/routers/auth.py` - Endpoints de registro con plan
- `backend/app/models/__init__.py` - Modelo User con plan_type

---

## 3. Frontend Actualizado

### Nuevas Páginas
- `/pricing` - Comparación de planes con features
- `/register?plan=starter` - Registro con plan preseleccionado

### Dashboard Mejorado
- Indicador de plan actual en header
- Barra de uso mensual en sidebar
- Alerta al 80% de límite
- Badge de "datos reales" en resultados
- Dirección completa del RUC consultado

### Landing Page
- Link a pricing en header
- CTA para ver planes
- Énfasis en "datos reales"

---

## 4. Variables de Entorno Requeridas

### Backend (.env)
```bash
# Base de datos
DATABASE_URL=postgresql://user:pass@host:5432/conflictzero
REDIS_URL=redis://host:6379/0

# Seguridad
SECRET_KEY=tu_secret_key_seguro

# APIs Externas (REQUERIDO)
PERUAPI_TOKEN=tu_token_peruapi
DECOLECTA_API_KEY=tu_key_decolecta  # Opcional, fallback

# AWS
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_REGION=us-east-1
S3_BUCKET=conflictzero-certificados-prod
```

### AWS Lambda
```bash
PERUAPI_TOKEN=tu_token_peruapi
S3_BUCKET=conflictzero-certificados-prod
```

### Frontend
```bash
NEXT_PUBLIC_API_URL=https://tu-api-gateway.amazonaws.com/prod
```

---

## 5. Cómo Obtener PERUAPI_TOKEN

1. Ir a https://peruapi.com
2. Crear cuenta gratuita (solo email y contraseña)
3. Verificar email
4. Ir al panel de control
5. Copiar el API Token
6. Pegar en variables de entorno

**Límites del plan free:**
- 100 consultas por día
- 1,000 consultas por mes
- Datos reales de SUNAT

---

## 6. Deploy Paso a Paso

### Paso 1: Configurar Variables de Entorno
```bash
# En AWS Lambda
aws lambda update-function-configuration \
  --function-name conflictzero-api \
  --environment "Variables={PERUAPI_TOKEN=tu_token,S3_BUCKET=tu_bucket}"
```

### Paso 2: Deploy del Lambda
```bash
cd aws/lambda
# Subir lambda_function_v6.py a AWS Lambda
# Configurar API Gateway:
#   GET /consulta-osce/{ruc}
#   GET /generar-certificado/{ruc}
```

### Paso 3: Deploy del Backend
```bash
cd backend
docker build -t conflictzero-backend .
# Deploy en ECS/Fargate o similar
```

### Paso 4: Deploy del Frontend
```bash
cd frontend
npm install
npm run build
# Deploy en Vercel/Netlify
```

---

## 7. Verificación Post-Deploy

### Test 1: Datos Reales
```bash
curl "https://tu-api.com/consulta-osce/20100017491"
```
Esperado:
```json
{
  "success": true,
  "datos_reales": true,
  "data": {
    "ruc": "20100017491",
    "razon_social": "INTERBANK S.A.",
    "estado_sunat": "ACTIVO",
    "direccion": "...",
    "fuentes_datos": { "sunat": "peruapi_sunat" }
  }
}
```

### Test 2: Sin API Key (Debe Fallar)
- Remover PERUAPI_TOKEN temporalmente
- La consulta debe retornar 503
- Mensaje: "Configure PERUAPI_TOKEN para datos reales"

### Test 3: Planes
```bash
# Registrar usuario con plan Starter
curl -X POST "https://tu-api.com/auth/register?plan=starter" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"12345678","full_name":"Test"}'
```

---

## 8. Diferenciación Clara

| Aspecto | Demo/Prueba | Producción |
|---------|-------------|------------|
| Datos SUNAT | Simulados | Reales vía Perú API |
| Datos OSCE | Mock | Scraper real (con fallback) |
| Nombres empresa | Generados | Reales de SUNAT |
| Direcciones | Ficticias | Reales del RUC |
| Sanciones | Aleatorias | Reales de OSCE/TCE |

---

## 9. Archivos Clave Modificados

### Backend
- `backend/app/core/config.py` - Nueva config PERUAPI_TOKEN
- `backend/app/services/external_api.py` - Datos reales obligatorios
- `backend/app/services/verification.py` - Sin mocks
- `backend/app/routers/auth.py` - Registro con planes

### Frontend
- `frontend/app/pricing/page.tsx` - **NUEVO**
- `frontend/app/register/page.tsx` - Plan seleccionable
- `frontend/app/dashboard/page.tsx` - Datos reales visibles
- `frontend/app/dashboard/layout.tsx` - Info de plan
- `frontend/app/page.tsx` - Link a pricing

### AWS Lambda
- `aws/lambda/lambda_function_v6.py` - Perú API integrado

---

## 10. Checklist Final

- [ ] PERUAPI_TOKEN configurado en Lambda
- [ ] PERUAPI_TOKEN configurado en Backend
- [ ] S3_BUCKET configurado
- [ ] Base de datos migrada
- [ ] Frontend deployado
- [ ] Test de RUC real pasa
- [ ] Test de datos reales confirma fuente "peruapi_sunat"
- [ ] Página de pricing visible
- [ ] Registro con plan funciona
- [ ] Dashboard muestra uso del plan

---

## Contacto

Para soporte o dudas:
- Documentación: `/root/.openclaw/workspace/conflict-zero/DEPLOY_PRODUCCION.md`
- Checklist: `/root/.openclaw/workspace/conflict-zero/PRODUCTION_CHECKLIST.md`

**El sistema está listo para producción con datos 100% reales.**
