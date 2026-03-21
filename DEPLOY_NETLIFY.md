# Deploy del Frontend a Netlify

## Estado Actual: ✅ LISTO PARA DEPLOY

El frontend está configurado para usar:
- **API Gateway** para consultas de RUC (datos reales de SUNAT)
- **Exportación estática** compatible con Netlify

---

## Configuración Actual

### Archivos de Configuración

**`next.config.js`** - Ya configurado:
```javascript
output: 'export',    // Exporta HTML estático
distDir: 'out',      // Carpeta de salida
images: { unoptimized: true }  // Para static export
```

**`netlify.toml`** - Creado:
```toml
[build]
  command = "npm run build"
  publish = "out"
```

**`.env.local`** - Variables de entorno:
```
NEXT_PUBLIC_API_URL=https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod
```

---

## Opción 1: Deploy con Netlify CLI (Recomendado)

### Paso 1: Instalar Netlify CLI
```bash
npm install -g netlify-cli
```

### Paso 2: Login
```bash
netlify login
```

### Paso 3: Build y Deploy
```bash
cd /root/.openclaw/workspace/conflict-zero/frontend

# Build
npm run build

# Deploy (primera vez)
netlify init
# Seguir instrucciones interactivas

# Deploy (siguientes veces)
netlify deploy --prod --dir=out
```

---

## Opción 2: Deploy con Script Automático

```bash
cd /root/.openclaw/workspace/conflict-zero/frontend
./deploy-netlify.sh
```

---

## Opción 3: Deploy Manual (Drag & Drop)

### Paso 1: Build local
```bash
cd /root/.openclaw/workspace/conflict-zero/frontend
npm install
npm run build
```

### Paso 2: Deploy
1. Ve a https://app.netlify.com/drop
2. Arrastra la carpeta `out/` (generada después del build)
3. ¡Listo! Tu sitio estará online en segundos

---

## Opción 4: Deploy desde GitHub (CI/CD)

### Paso 1: Subir a GitHub
```bash
git add .
git commit -m "Frontend listo para producción"
git push origin main
```

### Paso 2: Conectar en Netlify
1. Ve a https://app.netlify.com
2. Click "Add new site" → "Import an existing project"
3. Selecciona GitHub y tu repositorio
4. Configuración de build:
   - **Build command:** `npm run build`
   - **Publish directory:** `out`
5. Agregar variables de entorno:
   - `NEXT_PUBLIC_API_URL` = `https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod`
6. Click "Deploy site"

---

## Configurar Variables de Entorno en Netlify

### Opción A: Via Netlify Dashboard
1. Ve a tu sitio en Netlify
2. Site settings → Environment variables
3. Agrega:
   - `NEXT_PUBLIC_API_URL` = `https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod`
   - `NEXT_PUBLIC_BACKEND_URL` = `URL_DE_TU_BACKEND`

### Opción B: Via CLI
```bash
netlify env:set NEXT_PUBLIC_API_URL https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod
```

---

## Verificación Post-Deploy

### Test 1: Página principal carga
Visita: `https://tu-dominio.netlify.app`

### Test 2: Consulta de RUC funciona
1. Ingresa RUC: `20100017491`
2. Click en "Verificar"
3. Deberías ver:
   - ✅ "Datos reales de SUNAT/OSCE/TCE"
   - Razón social: "INTEGRATEL PERÚ S.A.A."
   - Fuente: `peruapi_sunat`

### Test 3: Planes visibles
Visita: `https://tu-dominio.netlify.app/pricing`

---

## URLs del Sistema

| Componente | URL |
|------------|-----|
| API Gateway | https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod |
| Lambda | conflictzero-api-real |
| Frontend (local) | http://localhost:3000 |
| Frontend (Netlify) | Pendiente de deploy |

---

## Troubleshooting

### Error: "Image optimization not supported"
Ya está solucionado en `next.config.js` con `images: { unoptimized: true }`

### Error: "Page not found" en rutas dinámicas
Para Next.js con exportación estática, las rutas dinámicas necesitan `generateStaticParams`.
El proyecto ya está configurado para esto.

### Error CORS
Si ves errores de CORS:
1. Verificar que `NEXT_PUBLIC_API_URL` esté configurada
2. El Lambda ya tiene CORS configurado para permitir `*` (cualquier origen)

---

## Comandos Útiles

### Build local
```bash
npm run build
```

### Preview local
```bash
npx serve out
```

### Ver logs de deploy
```bash
netlify deploy --prod --dir=out --debug
```

---

## Notas Importantes

1. **Exportación estática:** Next.js genera HTML estático en la carpeta `out/`
2. **No hay server-side rendering:** Todo es estático, el frontend llama a la API Gateway
3. **Variables de entorno:** Deben empezar con `NEXT_PUBLIC_` para estar disponibles en el cliente
4. **API Gateway:** Ya está configurado con CORS para permitir peticiones desde cualquier dominio

---

## Soporte

Si tienes problemas:
1. Verifica que `NEXT_PUBLIC_API_URL` esté configurada correctamente
2. Revisa los logs de build en Netlify
3. Prueba la API Gateway directamente con curl
