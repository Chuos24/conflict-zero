# Conflict Zero — Plan de Producto y Estado del Sistema

**Última actualización:** 2026-04-12  
**Mantenido por:** Santiago + Kimi Claw (agente de desarrollo)

---

## 1. Qué es Conflict Zero

Plataforma SaaS premium de verificación predictiva de riesgo para RUCs peruanos.  
Evalúa si es seguro contratar a un proveedor consultando SUNAT (deuda), OSCE (inhabilitaciones) y TCE/RNP (sanciones).

**Mercado objetivo:** Empresas peruanas que contratan proveedores (contratación pública y privada).  
**Posicionamiento:** Premium UHNW — sin plan gratuito. Diseño dark/gold.  
**URL producción:** czperu.com / API en Render

---

## 2. Planes y Precios (Soles — Valores Finales)

| Plan | Precio | Consultas/mes | Historial | Compare RUCs | Features clave |
|------|--------|---------------|-----------|--------------|----------------|
| **Essential** | S/ 400/mes | 1,000 | 90 días | 2 | PDF certs |
| **Professional** | S/ 800/mes | 5,000 | Ilimitado | 5 | PDF, API access, bulk upload, priority support, custom scoring |
| **Enterprise** | S/ 2,500/mes | 100,000 | Ilimitado | 10 | Todo lo anterior + webhooks, dedicated manager |

**No existe plan gratuito.** El registro web crea la cuenta y el equipo activa el plan manualmente tras confirmar el pago (transferencia bancaria, Yape, etc.).

**Fuente de verdad para precios:** `app/routers/auth.py` → `PLAN_CONFIG`

---

## 3. Stack Tecnológico en Producción

| Capa | Tecnología | Host |
|------|-----------|------|
| Backend API | Python 3.11 + FastAPI + SQLAlchemy | Render |
| Base de datos | PostgreSQL 15 | Render (interno) |
| Frontend | Next.js 14 + TypeScript + Tailwind | Netlify |
| Email | SendGrid | - |
| SUNAT/OSCE data | Perú API (`PERUAPI_TOKEN`) + Decolecta (fallback) | - |
| Cache | Redis (opcional, no crítico en free tier) | - |

**Nota:** Existe un backend Node.js/TypeScript experimental en `backend/src/`. No está en producción. Es un MVP paralelo de exploración. No tocar para trabajo de producción.

---

## 4. Arquitectura de Routers (Producción)

```
app/
├── main.py              # Entry point — Render ejecuta esto
├── api_v3.py            # ⚠️ LEGACY — NO MODIFICAR
└── routers/
    ├── auth.py          # Login, register, API key, upgrade-plan (admin)
    ├── verification.py  # POST /verify/, GET /verify/history
    ├── compare.py       # POST /compare (multi-RUC)
    ├── dashboard.py     # GET /dashboard/stats, /dashboard/usage
    ├── admin.py         # record-payment, activate-plan, pending-activations
    ├── notifications.py # Emails transaccionales
    ├── consulta.py      # Consulta completa con scoring
    ├── debug.py         # /debug/env (protegido con ADMIN_TOKEN)
    └── health.py        # Health checks
```

**Regla:** Nuevos endpoints van en `app/routers/`. Nunca en `api_v3.py`.

---

## 5. Columna de Plan Canónica

El modelo `User` tiene **dos columnas** de plan (deuda técnica histórica):

| Columna | Tipo | Valores | Estado |
|---------|------|---------|--------|
| `plan_type` | String | essential / professional / enterprise | **✅ CANÓNICA — usar esta** |
| `plan` | String | free / starter / professional / enterprise | ⚠️ **DEPRECADA** |

**Decisión:** `plan_type` es la fuente de verdad. Todo el sistema de validación de límites (`compare.py`, `verification.py`, `auth.py`) lee `plan_type`.

**Regla para migraciones y código nuevo:** Solo escribir y leer `plan_type`. La columna `plan` se mantiene temporalmente para no romper queries legacy, pero no debe usarse en lógica nueva.

**`/admin/activate-plan`** ya escribe ambas columnas en paralelo para compatibilidad mientras se depreca `plan`.

---

## 6. "Mi Red" — Monitoreo de Proveedores

### Qué existe HOY en código

| Componente | Estado | Dónde |
|------------|--------|-------|
| Modelo `SupplierAlert` (DB) | ✅ Listo | `app/models/__init__.py` |
| Modelo `CompanySnapshot` (DB) | ✅ Listo | `app/models/__init__.py` |
| Detección de cambios diseñada | ✅ Documentada | `docs/ML_ARCHITECTURE.md` |
| **Endpoints de API** | ❌ No existen | — |
| **Job de re-verificación** | ❌ No existe | — |
| **Email al detectar cambio** | ❌ No conectado | — |

### Qué falta para que funcione

1. `POST /network/add` — agregar RUC a watchlist del usuario
2. `DELETE /network/{ruc}` — quitar RUC de watchlist
3. `GET /network/` — listar RUCs monitoreados con su último estado
4. `GET /network/alerts` — ver alertas no leídas
5. `PATCH /network/alerts/{id}/read` — marcar alerta como leída
6. Cron job que re-verifica todos los RUCs activos 1x/día y crea `SupplierAlert` si hay cambio
7. Hook en el job que dispara email vía `/notifications/send-welcome` (adaptar template)

### Por qué es prioritario

Es el feature que convierte el producto de "consulta puntual" a "servicio continuo". Justifica renovación mensual y es el principal argumento de upsell a Professional/Enterprise.

---

## 7. Deuda Técnica Priorizada

### P0 — Bloqueante para cobrar (resolver esta semana)

| # | Deuda | Impacto | Dónde |
|---|-------|---------|-------|
| 1 | ~~Plan activation escribía solo `plan`, sistema lee `plan_type`~~ | ~~Clientes pagan y no reciben su plan~~ | ✅ **RESUELTO 2026-04-12** |
| 2 | ~~`user_id` era `int` en admin, DB usa UUID strings~~ | ~~No se podían registrar pagos~~ | ✅ **RESUELTO 2026-04-12** |
| 3 | Pasarela de pagos real (Culqi o Izipay para Perú) | Sin esto el cobro es 100% manual | `payments.py` (vacío) |

### P1 — Seguridad producción

| # | Deuda | Impacto | Dónde |
|---|-------|---------|-------|
| 4 | ~~Endpoints de setup/debug sin autenticación exponían credenciales~~ | ~~Vulnerabilidad crítica~~ | ✅ **RESUELTO 2026-04-12** |
| 5 | ~~Cualquier usuario podía hacer upgrade-plan gratis~~ | ~~Revenue leak~~ | ✅ **RESUELTO 2026-04-12** |
| 6 | `hashed_password = "temp:plaintext"` almacena contraseñas en claro | Si DB se compromete, passwords expuestas | `auth.py:155` |
| 7 | `ADMIN_TOKEN` hardcoded como `'CZ2026ADM'` en `admin.py` y `debug.py` | Asegurar que la env var esté configurada en Render | Env vars Render |

### P2 — Producto (próximas 2 semanas)

| # | Feature | Valor | Esfuerzo |
|---|---------|-------|---------|
| 8 | Mi Red / Supplier Watchlist | Alto — retención y upsell | Medio (modelo ya existe) |
| 9 | Pasarela de pagos Culqi/Izipay | Alto — automatizar cobros | Alto |
| 10 | PDF de certificados | Medio — feature de plan pago prometido | Medio |
| 11 | Rate limiting real por plan en `/verify/public` | Medio — ahora es honor system | Bajo |

### P3 — Backlog

| # | Item |
|---|------|
| 12 | Exportación de datos (CSV bulk) para Enterprise |
| 13 | Webhooks para notificaciones en tiempo real (Enterprise) |
| 14 | Tests unitarios (pytest) — cero cobertura actualmente |
| 15 | `dashboard/usage` devuelve `reset_date = "Primer día del próximo mes"` (string, no fecha real) |
| 16 | Migración Render → Railway o Fly.io si el problema de cache persiste |
| 17 | Eliminar columna `plan` de DB una vez que todos los registros usen `plan_type` |

---

## 8. Algoritmo de Scoring

```
score = (sunat_score × 0.30) + (osce_score × 0.40) + (ml_score × 0.30)

sunat_score  = 100 - log(deuda) normalizado
osce_score   = 100 si sin sanciones vigentes; escala a 0 según gravedad
ml_score     = 100 - (indicadores_anomalía × 15)
```

| Score | Nivel |
|-------|-------|
| 80–100 | Bajo |
| 60–79 | Moderado |
| 40–59 | Alto |
| 0–39 | Crítico |

**Bug conocido:** RUC `20529400790` muestra score 50 (debería ser ~95). Los datos en DB son correctos. Problema de cache en Render — no se aplica el código actualizado. Pendiente redeploy manual desde Render Dashboard.

---

## 9. Jobs Automáticos Activos

| Job | Frecuencia | Estado |
|-----|-----------|--------|
| Blog diario | 6 AM | ✅ Activo |
| Sync OSCE/TCE | 3 AM | ✅ Activo |
| Health check | Cada hora | ✅ Activo |
| Re-verificación proveedores (Mi Red) | — | ❌ No implementado |

---

## 10. Flujo de Alta de Cliente (Hoy)

```
1. Cliente llena formulario en czperu.com
       ↓
2. POST /auth/register-web — crea usuario inactivo, envía email con password temporal
       ↓
3. Admin confirma pago (transferencia/Yape) → POST /admin/record-payment
       ↓
4. Admin activa plan → POST /admin/activate-plan (escribe plan_type + plan + monthly_limit)
       ↓
5. Cliente recibe email y puede hacer login
```

**Punto de falla actual:** Pasos 3-4 son manuales. No hay pasarela automática.

---

## 11. APIs Externas y Credenciales

| API | Variable de entorno | Propósito |
|-----|--------------------|-----------| 
| Perú API | `PERUAPI_TOKEN` | Fuente primaria SUNAT — datos reales |
| Decolecta | `DECOLECTA_TOKEN` | Fallback SUNAT/OSCE |
| SendGrid | `SENDGRID_API_KEY` | Emails transaccionales |
| Admin token | `ADMIN_TOKEN` | Protege endpoints admin (default: CZ2026ADM — cambiar en Render) |
| JWT | `JWT_SECRET` | Firma tokens JWT |

---

## 12. Decisiones de Diseño Registradas

| Decisión | Razón |
|----------|-------|
| Sin plan gratuito | Posicionamiento premium UHNW. Demo vía `/verify/public` con rate limiting |
| Pagos manuales primero | Validar mercado antes de integrar pasarela. Culqi/Izipay para Fase 2 |
| PostgreSQL en Render | Simplicidad de deploy. Migrar si escala requiere más |
| `plan_type` como columna canónica | Ya era la que leía todo el sistema. `plan` es accidente histórico |
| Nuevos features en `app/routers/` | `api_v3.py` es monolito legacy con código crítico — no tocar |
