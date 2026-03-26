# Configuración de APIs SUNAT en Render

## Variables de Entorno Requeridas

### 1. FACTILIZA_TOKEN (Nueva - Prioridad 1)
```
Key: FACTILIZA_TOKEN
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDY0OCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.d_-YT6RuTIrq-RZj1TO6Q6r3EG2NL4MRO9odkcaGDYA
```

### 2. APIPERU_TOKEN (Prioridad 2)
```
Key: APIPERU_TOKEN
Value: 3260b3944acfbcbb78fe44d417ec5eb67da57a40f28a682490027b65eb5544da
```

### 3. PERUAPI_TOKEN (Prioridad 3 - Opcional)
```
Key: PERUAPI_TOKEN
Value: (obtener de peruapi.com)
```

### 4. BUSCARUC_TOKEN (Prioridad 4 - Actualmente bloqueado)
```
Key: BUSCARUC_TOKEN
Value: eyJ1c2VySWQiOjU0NzAsInVzZXJUb2tlbklkIjo1NDY5fQ.QK8EdbO21g2rCk3jqUqdOf3pKKhNZqymmG30RTbMURhtp7-JPJcPX3xHXAaH46qAoHrTnQLgqTGo1yY1zu64QfPvLux0EbX2R9V_1tAy8Fdos2-Z-_XXTe7Wi0lRTBK55uh_zCm5zCiYs7VJBW4T9e2mZdd6EaXYaXOwEybmseE
```
Nota: BuscarUC actualmente bloquea peticiones desde Render.

## Arquitectura de Fallback

```
1. Factiliza.com (POST /api/ruc)        → Fuente 1
2. APIPeru.dev (POST /api/ruc)          → Fuente 2  
3. PeruAPI.com (GET /api/ruc/{ruc})      → Fuente 3
4. BuscarUC.com (POST /api/v1/ruc)      → Fuente 4 (bloqueado)
5. Base de datos local                   → Fallback final
```

## Pasos para Configurar en Render

1. Ir a https://dashboard.render.com
2. Seleccionar el servicio `conflict-zero-api`
3. Ir a la pestaña "Environment"
4. Agregar cada variable con su Key y Value
5. Click "Save Changes"
6. El servicio se reiniciará automáticamente

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
  "fuente": "factiliza_api",
  "success": true
}
```
