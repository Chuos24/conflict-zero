# TAREAS PENDIENTES - Conflict Zero

## ⚠️ URGENTE - Requiere atención inmediata

### 1. Actualizar RUC 20529400790 en Producción
**Status**: 🔴 BLOQUEADO - Render no aplica cambios
**Creado**: 2026-03-26
**Commits**:
- `4dc1296` - Script update_sancion_20529400790.py
- `8c5de7a` - Workflow fix sanción (DB detalle)
- `b385ad3` - Workflow fix osce_risk_data (DB agregada)
- `61013b4` - Fix scoring.py recuperación temporal en fallback
- `29d801b` - Fix campo 'status' vs 'estado'
- `38cd3cb` - Script diagnóstico
- `30552ee` - Diagnóstico simplificado
- `3c8bc84` - Force redeploy scoring

**Diagnóstico DB**: ✅ TODOS LOS DATOS CORRECTOS
- osce_risk_data: sanciones_vigentes=0, score_osce_anual=95
- osce_sanciones_detalle: estado='VENCIDA', fecha_fin='2025-12-31'
- Análisis: "Debería aplicar recuperación temporal"

**Problema**: Render no aplica el código actualizado
- Score API: 50 (debería ser ~95)
- Risk Level: high (debería ser low/medium)

**Causas posibles**:
1. Cache de Docker en Render
2. Build fallando silenciosamente
3. Código diferente entre local y producción

**Soluciones a intentar**:
- [ ] Verificar dashboard de Render por errores de build
- [ ] Forzar redeploy manual desde Render Dashboard
- [ ] Hacer cambio en otro archivo (main.py) para invalidar cache
- [ ] Verificar si hay error en runtime (logs de Render)
- [ ] Considerar migrar a otro servicio (Railway, Fly.io)

---

## 🔄 TAREAS RECURRENTES (Automáticas)

### Blog Diario (6 AM) ✅
- Job: conflict-zero-blog-daily
- Status: Activo
- Último run: OK

### Sync OSCE/TCE (3 AM) ✅
- Job: conflict-zero-osce-sync
- Status: Activo
- Próximo run: Mañana 3 AM

### Health Check (Cada hora) ✅
- Job: conflict-zero-health-check
- Status: Activo

---

## 📋 BACKLOG - Mejoras Futuras

### 1. Actualización Masiva de Sanciones Reducidas
**Prioridad**: Media
**Descripción**: Hay otras sanciones que podrían haber sido reducidas por retroactividad benigna. Investigar casos similares.

### 2. Sistema de Alertas por Email/Notificación
**Prioridad**: Baja
**Descripción**: Cuando un RUC cambia de estado (VIGENTE → VENCIDA), notificar a usuarios que lo tienen en favoritos.

### 3. Integración RNP Real (no solo scraping)
**Prioridad**: Media
**Descripción**: El scraper actual es básico. Mejorar para obtener todos los datos RNP/TCE.

### 4. Optimización de Queries
**Prioridad**: Baja
**Descripción**: Agregar índices adicionales si las consultas se vuelven lentas.

---

## 🐛 BUGS CONOCIDOS

### 1. Redis Warning en API
**Status**: No crítico
**Descripción**: API muestra "redis: down" pero funciona sin problemas (Render free tier sin Redis)

### 2. Fechas en verificar.html N/A a veces
**Status**: Parcialmente resuelto
**Descripción**: Cuando la API no responde, el fallback no tiene fechas detalladas. Considerar cache local.

---

## ✅ COMPLETADAS RECIENTEMENTE

- [x] Fix Pydantic V2 (regex → pattern)
- [x] Fix API routing (/api/v1 prefix)
- [x] Fórmula "cruda pero justa" implementada
- [x] Fechas de inicio/fin en verificar.html
- [x] Script update_sancion_20529400790.py creado

---

## 📞 CONTACTOS/ACCESOS NECESARIOS

- GitHub: Configurar GH_TOKEN para ejecutar workflows remotamente
- Render: API key ya configurada en .env.infrastructure
- Vercel: Auto-deploy en push a main

---

**Nota para mí (Kimi Claw)**: Revisar este archivo durante heartbeats. Si hay items en URGENTE por más de 24h, ejecutar sin esperar.
