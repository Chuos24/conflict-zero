# 🔐 Acceso Admin - Conflict Zero

## Generar Token de Administrador

Para usar los endpoints administrativos (`/admin/*`), necesitas un token JWT.

### Paso 1: Obtener Token

**Endpoint:** `POST /api/v1/auth/admin/token`

**Request:**
```bash
curl -X POST https://conflict-zero-api.onrender.com/api/v1/auth/admin/token \
  -H "Content-Type: application/json" \
  -d '{
    "email": "founder@conflictzero.com",
    "password": "CZ2025!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400,
  "expires_at": "2026-03-27T20:00:00",
  "user": {
    "email": "founder@conflictzero.com",
    "is_admin": true
  }
}
```

> ⚠️ **IMPORTANTE**: El token dura 24 horas. Guardalo de forma segura.

---

## Usar Token en Endpoints Admin

### Listar Sanciones de un RUC

```bash
curl -X GET "https://conflict-zero-api.onrender.com/api/v1/admin/sanciones/list/20529400790" \
  -H "Authorization: Bearer TU_TOKEN_AQUI"
```

### Actualizar Sanción

```bash
curl -X POST "https://conflict-zero-api.onrender.com/api/v1/admin/sanciones/update" \
  -H "Authorization: Bearer TU_TOKEN_AQUI" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "ruc=20529400790" \
  -d "numero_resolucion=4162-2023-TCE-S4" \
  -d "nuevo_estado=VENCIDA" \
  -d "fecha_fin=2025-12-31" \
  -d "nota=Reducido por Resolución 6981-2025-TCP-S4"
```

**Parámetros:**
- `ruc`: RUC de la empresa (11 dígitos)
- `numero_resolucion`: Número de resolución (parcial, ej: "4162" funciona)
- `nuevo_estado`: `VIGENTE` o `VENCIDA`
- `fecha_fin`: Fecha de fin en formato `YYYY-MM-DD` (opcional)
- `nota`: Nota sobre el cambio (opcional)

---

## 🔄 Sincronización Diaria (Automática)

### Qué hace

El script `sync_osce_risk_daily.py` recalcula la tabla `osce_risk_data` desde `osce_sanciones_detalle`:

1. ✅ Cuenta sanciones vigentes vs vencidas
2. ✅ Aplica fórmula de recuperación temporal automáticamente
3. ✅ Actualiza scores en `osce_risk_data`
4. ✅ Detecta discrepancias

### Ejecutar Manualmente

En el Shell de Render:
```bash
cd backend
python scripts/sync_osce_risk_daily.py
```

### Configurar Cron (Automático)

En Render Dashboard:
1. Ir a tu servicio `conflict-zero-api`
2. Pestaña **"Cron Jobs"**
3. Agregar nuevo job:
   - **Command:** `cd backend && python scripts/sync_osce_risk_daily.py`
   - **Schedule:** `0 3 * * *` (3 AM diario)

---

## 📋 Casos de Uso Comunes

### Caso 1: Sanción Vencida pero Sigue Marcada como Vigente

```bash
# 1. Obtener token
TOKEN=$(curl -s -X POST https://conflict-zero-api.onrender.com/api/v1/auth/admin/token \
  -H "Content-Type: application/json" \
  -d '{"email":"founder@conflictzero.com","password":"CZ2025!"}' | jq -r '.access_token')

# 2. Actualizar sanción
curl -X POST "https://conflict-zero-api.onrender.com/api/v1/admin/sanciones/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "ruc=20529400790" \
  -d "numero_resolucion=4162-2023-TCE-S4" \
  -d "nuevo_estado=VENCIDA" \
  -d "fecha_fin=2025-12-31"

# 3. Verificar cambio
curl -s "https://conflict-zero-api.onrender.com/api/v1/consulta-completa/20529400790" | jq '.score'
```

### Caso 2: Corregir Muchos RUCs

Si hay muchos casos, mejor correr la sincronización completa:
```bash
cd backend
python scripts/sync_osce_risk_daily.py
```

Esto recalcula TODOS los RUCs automáticamente.

---

## 🛡️ Seguridad

- **Solo el founder** (`founder@conflictzero.com`) puede generar tokens admin
- Los tokens duran **24 horas**
- Los endpoints admin requieren header `Authorization: Bearer {token}`
- Todos los cambios se loguean en el campo `motivo` de la sanción

---

## 🆘 Troubleshooting

### "Credenciales incorrectas"
- Verificar que el usuario founder existe: `GET /api/v1/auth/setup/create-founder`
- Resetear contraseña: `GET /api/v1/auth/setup/reset-founder-password`

### "Se requieren privilegios de administrador"
- El usuario no tiene `is_admin = true` en la base de datos
- Corregir desde el shell de Render o usar el endpoint de setup

### El score no cambia después de actualizar
- Esperar 2-5 minutos (cache de la API)
- Forzar recarga: agregar `?nocache=1` a la URL
- Verificar que `osce_risk_data` se actualizó: usar endpoint `/admin/sanciones/list/{ruc}`

---

**Última actualización:** 2026-03-26
