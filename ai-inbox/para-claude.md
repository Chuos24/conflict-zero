# Auditoría Completa — czperu.com
**Fecha:** 2026-04-13  
**Auditor:** Kimi Claw  
**Tipo:** Modo Dark Factory — Auditoría nocturna completa

---

## 🚨 RESUMEN EJECUTIVO

**Estado general:** Funcional pero con brechas críticas en endpoints de producción.

| Categoría | Estado |
|-----------|--------|
| Landing (frontend) | ✅ Operativo |
| API core (consulta RUC) | ✅ Operativo |
| Mi Red (endpoints básicos) | ✅ Operativo |
| **Sistema de Invitaciones** | 🔴 **ROTO en producción** |
| **Alertas API** | 🔴 **Faltan en producción** |
| **Health endpoint v3** | 🟡 **No existe** |
| Cache Zamora | ✅ Aparentemente resuelto |

---

## 🔴 CRÍTICO — IMPACTO ALTO

### 1. Sistema de Invitaciones NO existe en backend de producción

**Problema:** Los endpoints de invitaciones están SOLO en `api_v3.py` (legacy). Render ejecuta `app.main:app` que usa los routers modulares en `app/routers/`, donde **NO hay** un router de invitaciones.

**Esto significa que "Mi Red" está técnicamente roto:**
- ❌ `POST /api/v3/invitations` → **404 Not Found**
- ❌ `GET /api/v3/invitations/validate` → **404 Not Found**
- ❌ `GET /api/v3/invitations/mis-invitados` → **404 Not Found**

**Validación:**
```bash
curl https://conflict-zero-api.onrender.com/api/v3/invitations/mis-invitados
# Resultado: {"detail":"Not Found"}
```

**Impacto:** Los clientes Professional/Enterprise NO pueden invitar subcontratistas a su red. El botón "Invitar al Comité" en dashboard.html falla silenciosamente.

**Acción requerida:**
1. Migrar los 3 endpoints de invitaciones de `api_v3.py` a `app/routers/invitations.py`
2. Registrar el router en `app/main.py` con prefix `/api/v3`
3. Asegurar que usen los modelos de DB correctos (`invitations` table)
4. Deploy y probar flujo completo: crear invitación → validar token → registrar invitado → ver mis invitados

---

### 2. Endpoints de Alertas faltan en producción

**Problema:** Similar al anterior, los endpoints de alertas están en `api_v3.py` pero no en los routers de producción.

**Faltan:**
- ❌ `GET /api/v3/alerts`
- ❌ `GET /api/v3/alerts/triggered`
- ❌ `DELETE /api/v3/alerts/{alert_id}`

**Impacto:** Los usuarios no pueden ver ni gestionar sus alertas configuradas. La funcionalidad de monitoreo está incompleta.

**Acción requerida:** Migrar alertas de `api_v3.py` a `app/routers/alerts.py` y registrarlo en `app/main.py`.

---

## 🟡 MEDIO — IMPACTO MODERADO

### 3. Health endpoint `/api/v3/health` no existe

**Problema:** Solo existe `/api/v1/health`. El frontend y monitoreo externo pueden estar consultando v3 y fallando.

**Validación:**
```bash
curl https://conflict-zero-api.onrender.com/api/v3/health
# Resultado: {"detail":"Not Found"}
```

**Acción requerida:** Agregar `app.include_router(health_router, prefix="/api/v3")` en `app/main.py` (o crear un endpoint simple en v3).

---

### 4. Endpoints internos de diagnóstico faltan en producción

**Faltan:**
- `GET /api/v3/internal/cache-clear/{ruc}`
- `GET /api/v3/internal/cache-test/{ruc}`
- `GET /api/v3/internal/certs-check`
- `GET /api/v3/internal/db-check`
- `GET /api/v3/internal/redis-status`

**Impacto:** Sin herramientas de debugging en producción, resolver problemas como el cache de Zamora es más difícil.

**Acción requerida:** Crear `app/routers/internal.py` con estos endpoints (protegidos por admin token).

---

### 5. Páginas de frontend redirigen 307 a www.czperu.com

**Problema:** `czperu.com/pagina.html` retorna `307 Temporary Redirect` a `www.czperu.com/pagina.html`.

**Validación:**
```bash
curl -I https://czperu.com/verificar.html
# HTTP/2 307
# location: https://www.czperu.com/verificar.html
```

**Impacto:** Bajo. El contenido final carga correctamente (200 OK después del redirect). Pero puede afectar SEO ligeramente.

**Acción requerida:** Considerar configurar Vercel para que el dominio canónico sea `czperu.com` sin www, o asegurar que todos los links internos usen `www.czperu.com`.

---

## ✅ FUNCIONANDO CORRECTAMENTE

### 6. API de consulta RUC (Factiliza + Sunat)

**Estado:** ✅ Perfecto.

**Pruebas realizadas:**

| RUC | Fuente | Score | Nombre |
|-----|--------|-------|--------|
| 20521657021 | ruc_only | 97 | RUC 20521657021 |
| 20600955516 | ruc_only | 97 | RUC 20600955516 |
| 20100070970 | buscaruc_sunat | 96 | SUPERMERCADOS PERUANOS SOCIEDAD ANONIMA 'O ' S.P.S.A. |
| 20529400790 | buscaruc_sunat | 97 | CONSTRUCTORA ZAMORA JARA SAC |

**Nota:** El score de Zamora ahora muestra 97 (previamente había problema de cache). Parece resuelto tras los últimos deploys.

**CORS:** Correctamente configurado para `https://www.czperu.com`.

---

### 7. Endpoints de Mi Red (básicos)

**Estado:** ✅ Operativos.

```bash
GET /api/v3/network/         → 200 OK
GET /api/v3/network/alerts   → 200 OK
```

**El grafo D3.js en red.html carga correctamente.**

---

### 8. Admin de pagos

**Estado:** ✅ Operativo.

```bash
GET /api/v3/admin/pending-activations → 200 OK
GET /api/v3/admin/                    → 200 OK
```

**Pagos sin activar:** 0

---

### 9. Cron jobs configurados

**Estado:** ✅ Configurados en `render.yaml`.

- `conflict-zero-osce-sync` (3 AM UTC)
- `conflict-zero-health-check` (cada 30 min)
- `network-monitor-daily` (6 AM UTC)

---

## 📋 LISTA DE ENDPOINTS FALTANTES EN PRODUCCIÓN

Comparación entre `api_v3.py` (legacy, completo) vs `app/routers/` (producción, incompleto):

| Endpoint | Estado en Producción | Dónde está |
|----------|---------------------|------------|
| `POST /api/v3/invitations` | 🔴 **404** | Solo en api_v3.py |
| `GET /api/v3/invitations/validate` | 🔴 **404** | Solo en api_v3.py |
| `GET /api/v3/invitations/mis-invitados` | 🔴 **404** | Solo en api_v3.py |
| `GET /api/v3/alerts` | 🔴 **404** | Solo en api_v3.py |
| `GET /api/v3/alerts/triggered` | 🔴 **404** | Solo en api_v3.py |
| `DELETE /api/v3/alerts/{alert_id}` | 🔴 **404** | Solo en api_v3.py |
| `GET /api/v3/health` | 🟡 **404** | Solo en api_v3.py |
| `GET /api/v3/network/{ruc}` | 🟡 **404** | Solo en api_v3.py (demo) |
| `GET /api/v3/internal/*` | 🟡 **404** | Solo en api_v3.py |

---

## 🎯 TAREAS RECOMENDADAS PARA MAÑANA (ordenadas por impacto)

### Tarea 1 (Crítica): Migrar Sistema de Invitaciones a Producción
- Copiar endpoints de `api_v3.py` a `app/routers/invitations.py`
- Incluir: POST /invitations, GET /invitations/validate, GET /invitations/mis-invitados
- Registrar en `app/main.py`
- Probar flujo completo de invitación

### Tarea 2 (Crítica): Migrar Endpoints de Alertas a Producción
- Copiar endpoints de `api_v3.py` a `app/routers/alerts.py`
- Incluir: GET /alerts, GET /alerts/triggered, DELETE /alerts/{alert_id}
- Registrar en `app/main.py`

### Tarea 3 (Media): Agregar Health Endpoint v3
- Añadir `app.include_router(health_router, prefix="/api/v3")` en `app/main.py`
- Crear router `app/routers/internal.py` con endpoints de diagnóstico admin-only

---

## 📝 NOTAS ADICIONALES

- **Frontend landing:** Todas las páginas cargan visualmente bien (verificar.html, login.html, dashboard.html, red.html, admin.html).
- **D3.js en red.html:** Funciona correctamente.
- **Login:** Funciona, tokens JWT válidos por 7 días.
- **TODOs críticos en backend:** `app/services/snapshot_service.py:269` tiene pendiente "Enviar email si es high/critical".

---

*Auditoría generada automáticamente por Kimi Claw en modo Dark Factory.*
