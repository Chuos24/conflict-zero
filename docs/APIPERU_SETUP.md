# Configuración de APIPeru.dev en Render

## Variables de Entorno a Configurar

En tu servicio de Render (conflict-zero-api), agrega:

```
APIPERU_TOKEN=3260b3944acfbcbb78fe44d417ec5eb67da57a40f28a682490027b65eb5544da
```

## Pasos Manuales

1. Ir a https://dashboard.render.com
2. Seleccionar el servicio `conflict-zero-api`
3. Ir a "Environment"
4. Agregar nueva variable:
   - Key: `APIPERU_TOKEN`
   - Value: `3260b3944acfbcbb78fe44d417ec5eb67da57a40f28a682490027b65eb5544da`
5. Click "Save Changes"
6. El servicio se reiniciará automáticamente

## Arquitectura de Fuentes (Orden de Prioridad)

```
1. APIPeru.dev (POST /api/ruc) - Primaria
2. PeruAPI.com (GET /api/ruc/{ruc}) - Secundaria  
3. BuscarUC.com (POST /api/v1/ruc) - Terciaria
4. Base de datos local - Fallback final
```

## Estado del Código

✅ Commit b3af840 subido a GitHub
✅ Función `call_apiperu_dev()` implementada
✅ Test local exitoso: 85ms response time
⏳ Deploy en progreso (~2-3 minutos)

## Test Post-Deploy

```bash
curl https://conflict-zero-api.onrender.com/api/v1/sunat/ruc/20529400790
```

Respuesta esperada:
```json
{
  "ruc": "20529400790",
  "razon_social": "CONSTRUCTORA ZAMORA JARA SAC",
  "estado": "ACTIVO",
  "condicion": "HABIDO",
  "fuente": "apiperu_dev",
  ...
}
```
