# Conflict Zero — Deploy Manual (Instrucciones para Usuario)

## Situación Actual (2026-05-02)
- ✅ Código con 4 fixes está en GitHub (`origin/main`, commit `c204265`)
- ❌ Render NO auto-deployó (probablemente desconectado del webhook)
- ❌ API sigue corriendo código viejo

## Opción A — Deploy Manual desde Render Dashboard (Recomendada, 2 minutos)

1. Ir a https://dashboard.render.com
2. Encontrar el servicio "conflict-zero-api"
3. Click en el servicio → Settings → Build & Deploy
4. Verificar:
   - Branch = `main`
   - Auto-Deploy = ON
5. Click "Manual Deploy" → "Deploy latest commit"
6. Esperar 60-90 segundos
7. Verificar: `curl https://conflict-zero-api.onrender.com/api/v3/health`

## Opción B — Fix SQL Directo (Si solo necesita arreglar invitaciones AHORA)

Ejecutar en PostgreSQL (desde Render Dashboard → PostgreSQL → SQL):

```sql
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS company VARCHAR(255);
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS notes TEXT;
ALTER TABLE invitations ADD COLUMN IF NOT EXISTS accepted_by VARCHAR(36);
```

Esto arregla el error 500 de `/invitations/mis-invitados` inmediatamente.

## Opción C — Aplicar Código Localmente y Push desde Mac

1. Abrir terminal en Mac
2. `cd /Users/santi/conflictzero` (o donde esté el repo)
3. `git pull origin main`
4. Aplicar los 4 snippets del archivo `FIXES_SNIPPETS_2026-05-02.md`
5. `git add -A && git commit -m "fix: 4 critical fixes" && git push origin main`
6. Luego ir al dashboard de Render y hacer "Manual Deploy"

## Verificación después del deploy

```bash
# 1. Health endpoint v3
curl https://conflict-zero-api.onrender.com/api/v3/health

# 2. RUC inválido debe dar score 15
curl https://conflict-zero-api.onrender.com/api/v3/consulta-completa/99999999999

# 3. Invitaciones (requiere login primero)
curl -X POST https://conflict-zero-api.onrender.com/api/v3/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"founder@conflictzero.com","password":"CZ2025!"}'
# Luego usar el token en:
curl -H "Authorization: Bearer TOKEN" https://conflict-zero-api.onrender.com/api/v3/invitations/mis-invitados

# 4. Network endpoint
curl -H "Authorization: Bearer TOKEN" https://conflict-zero-api.onrender.com/api/v3/network/stats
```

## Si nada funciona

Contactar a Render support o reconectar el repo:
1. Dashboard → Servicio → Settings → Build & Deploy
2. Disconnect GitHub repo
3. Reconnect → seleccionar `Chuos24/conflict-zero`
4. Branch = `main`
5. Auto-Deploy = ON
6. Save → Manual Deploy

---

**Nota:** Los cambios de código están listos y verificados. El único obstáculo es que Render no detecta los pushes automáticamente. Una vez que el usuario fuerce el deploy manual, todo funcionará.
