# Conflict Zero - Configuración para Producción

## Estado Actual: Listo para Deploy

### ✅ Cambios Realizados

1. **Datos SUNAT Reales**
   - Integración con Perú API (fuente primaria)
   - Fallback a Decolecta API
   - Sin datos simulados en producción

2. **Planes Diferenciados**
   - Free: 100 consultas/mes
   - Starter: $400/mes, 1,000 consultas
   - Pro: $800/mes, 5,000 consultas
   - Enterprise: $2,000/mes, ilimitado

3. **Frontend Actualizado**
   - Página de pricing completa
   - Dashboard con datos reales
   - Indicadores de fuente de datos

## Variables de Entorno Requeridas

### Backend (.env)
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/conflictzero

# Redis
REDIS_URL=redis://host:6379/0

# JWT
SECRET_KEY=tu_secret_key_seguro_de_al_menos_32_caracteres

# APIs Externas (REQUERIDO para datos reales)
PERUAPI_TOKEN=tu_token_de_peruapi
DECOLECTA_API_KEY=tu_key_de_decolecta (fallback)

# AWS
AWS_ACCESS_KEY_ID=tu_access_key
AWS_SECRET_ACCESS_KEY=tu_secret_key
AWS_REGION=us-east-1
S3_BUCKET=conflictzero-certificados-prod

# Stripe (opcional, para pagos)
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

### AWS Lambda (Environment Variables)
```bash
S3_BUCKET=conflictzero-certificados-prod
PERUAPI_TOKEN=tu_token_de_peruapi
DECOLECTA_API_KEY=tu_key_de_decolecta (opcional)
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_API_URL=https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod
```

## Cómo Obtener PERUAPI_TOKEN

1. Ve a https://peruapi.com
2. Crea una cuenta gratuita
3. Ve al panel de control
4. Copia tu API Token
5. Configúralo en las variables de entorno

**Plan Free de Perú API:**
- 100 consultas/día
- 1,000 consultas/mes
- Datos reales de SUNAT

## Deploy Paso a Paso

### 1. Backend (AWS ECS/Fargate o similar)
```bash
cd backend
# Actualizar variables en .env
docker build -t conflictzero-backend .
docker push tu-registry/conflictzero-backend
# Deploy en tu plataforma cloud
```

### 2. Lambda (AWS)
```bash
cd aws/lambda
# Subir lambda_function_v6.py a AWS Lambda
# Configurar las variables de entorno
# Configurar API Gateway con rutas:
#   GET /consulta-osce/{ruc}
#   GET /generar-certificado/{ruc}
```

### 3. Frontend (Vercel/Netlify)
```bash
cd frontend
npm install
npm run build
# Deploy en Vercel/Netlify
```

## Verificación Post-Deploy

### Test 1: Consulta RUC
```bash
curl "https://tu-api.com/consulta-osce/20100017491"
```
Respuesta esperada:
```json
{
  "success": true,
  "data": {
    "ruc": "20100017491",
    "razon_social": "INTERBANK S.A.",
    "estado_sunat": "ACTIVO",
    "condicion": "HABIDO",
    "direccion": "...",
    ...
  },
  "datos_reales": true
}
```

### Test 2: Sin API Key (debe fallar)
```bash
# Remover PERUAPI_TOKEN temporalmente
# La consulta debe retornar error 503
```

## Diferenciación de Planes

| Feature | Free | Starter | Pro | Enterprise |
|---------|------|---------|-----|------------|
| Consultas/mes | 100 | 1,000 | 5,000 | ∞ |
| Datos SUNAT reales | ✅ | ✅ | ✅ | ✅ |
| Sanciones OSCE/TCE | ✅ | ✅ | ✅ | ✅ |
| Certificados PDF | ❌ | ✅ | ✅ | ✅ |
| Historial | ❌ | ✅ | ✅ | ✅ |
| API Access | ❌ | ❌ | ✅ | ✅ |
| Bulk Upload | ❌ | ❌ | ✅ | ✅ |
| Soporte | Email | Prioritario | Prioritario | 24/7 |

## Solución de Problemas

### "No se pudieron obtener datos de SUNAT"
- Verificar que PERUAPI_TOKEN esté configurado
- Verificar que la API key sea válida
- Revisar logs del Lambda

### "Datos simulados"
- Esto NO debe pasar en producción
- Verificar que no hay mocks habilitados
- Verificar variables de entorno

### Rate limiting
- Implementar caché (ya incluido, 1 hora)
- Considerar upgrade de plan en Perú API
- Usar Decolecta como fallback

## Contacto y Soporte

Para configuración Enterprise o soporte técnico:
- Email: soporte@czperu.com
- Web: https://czperu.com

---

**Nota importante:** Este sistema está diseñado para usar ÚNICAMENTE datos reales. No hay modo "demo" o "simulación" en producción.
