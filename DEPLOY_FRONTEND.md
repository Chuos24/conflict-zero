# Deploy del Frontend a Vercel

## Estado Actual: ✅ LISTO PARA DEPLOY

El frontend está configurado para usar:
- **API Gateway** para consultas de RUC (datos reales de SUNAT)
- **Backend** para autenticación e historial

---

## Configuración Actual

### Archivo `.env.local`
```
NEXT_PUBLIC_API_URL=https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod
NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
```

### API Configurada
- **URL:** https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod
- **Función:** Lambda `conflictzero-api-real`
- **Datos:** Reales vía Perú API

---

## Opción 1: Deploy a Vercel (Recomendado)

### Paso 1: Instalar Vercel CLI
```bash
npm i -g vercel
```

### Paso 2: Login
```bash
vercel login
```

### Paso 3: Deploy
```bash
cd /root/.openclaw/workspace/conflict-zero/frontend
vercel --prod
```

Sigue las instrucciones interactivas:
- Link to existing project? **No** (crear nuevo)
- Project name: **conflict-zero**
- Directory: **./** (enter)

### Paso 4: Configurar Variables de Entorno en Vercel
En el dashboard de Vercel:
1. Ve a tu proyecto
2. Settings → Environment Variables
3. Agrega:
   - `NEXT_PUBLIC_API_URL` = `https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod`
   - `NEXT_PUBLIC_BACKEND_URL` = `URL_DE_TU_BACKEND`

---

## Opción 2: Deploy Manual (Build Local)

### Paso 1: Build
```bash
cd /root/.openclaw/workspace/conflict-zero/frontend
npm run build
```

### Paso 2: La carpeta `out/` contiene los archivos estáticos
Sube los archivos de la carpeta `out/` a cualquier hosting estático:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages

---

## Verificación Post-Deploy

### Test 1: Página principal carga
Visita: `https://tu-dominio.vercel.app`

### Test 2: Consulta de RUC funciona
1. Ingresa RUC: `20100017491`
2. Click en "Verificar"
3. Deberías ver:
   - ✅ "Datos reales de SUNAT/OSCE/TCE"
   - Razón social: "INTEGRATEL PERÚ S.A.A."
   - Fuente: `peruapi_sunat`

### Test 3: Planes visibles
Visita: `https://tu-dominio.vercel.app/pricing`
Deberías ver los 4 planes (Free, Starter, Pro, Enterprise)

---

## URLs del Sistema

| Componente | URL |
|------------|-----|
| API Gateway | https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod |
| Lambda | conflictzero-api-real |
| Frontend (local) | http://localhost:3000 |
| Frontend (prod) | Pendiente de deploy |

---

## Comandos Útiles

### Verificar API Gateway
```bash
curl "https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod/consulta-osce/20100017491"
```

### Verificar Lambda directamente
```bash
aws lambda invoke \
  --function-name conflictzero-api-real \
  --payload '{"httpMethod": "GET", "pathParameters": {"ruc": "20100017491"}}' \
  response.json && cat response.json
```

---

## Notas Importantes

1. **El backend (FastAPI)** debe estar corriendo en algún lugar accesible
   - Opciones: AWS ECS, Railway, Render, o tu propio servidor
   - Actualiza `NEXT_PUBLIC_BACKEND_URL` con la URL real

2. **API Gateway ya está funcionando** con datos reales de SUNAT
   - No necesitas el backend para consultas de RUC
   - Solo necesitas backend para: login, registro, historial, pagos

3. **Si solo quieres consultas de RUC públicas**
   - Puedes usar solo el frontend + API Gateway
   - Sin necesidad de backend

---

## Soporte

Si tienes problemas:
1. Verifica que `NEXT_PUBLIC_API_URL` apunte a la API Gateway
2. Prueba la API Gateway directamente con curl
3. Revisa los logs de Vercel en el dashboard
