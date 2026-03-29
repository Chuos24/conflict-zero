# CI/CD Setup - GitHub Actions

## 🚀 Opción Rápida (Recomendada)

```bash
cd /root/.openclaw/workspace/conflict-zero
./deploy.sh "tu mensaje"
```

**Funciona ahora mismo.** Deploy en 90 segundos.

---

## 🔧 GitHub Actions (Setup en 2 min)

### Paso 1: Crear archivo
Ve a este link (abre editor directo):
```
https://github.com/new/main/.github/workflows/deploy.yml?filename=.github/workflows/deploy.yml
```

O manual:
1. Ve a https://github.com/Chuos24/conflict-zero
2. Click **Add file** → **Create new file**
3. Path: `.github/workflows/deploy.yml`

### Paso 2: Pegar contenido

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to Render
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          curl -X POST \
            -H "Authorization: Bearer $RENDER_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"clearCache":false}' \
            https://api.render.com/v1/services/srv-d6vagtfafjfc73cu0kdg/deploys
```

Click **Commit new file**

### Paso 3: Agregar Secret

1. Ve a **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Name: `RENDER_API_KEY`
4. Value: `rnd_TD2zaOUFhKiLOcvk5qQJNqxqAMKE`
5. Click **Add secret**

### ✅ Listo!

Ahora cada push a `main` que modifique `backend/` hará deploy automático.

Ver status en: https://github.com/Chuos24/conflict-zero/actions

---

## 📊 Comparativa

| Feature | deploy.sh | GitHub Actions |
|---------|-----------|----------------|
| Setup | ✅ Listo | ⚠️ 2 minutos |
| Tests | ❌ No | ✅ Sí |
| Team visibility | ❌ No | ✅ Dashboard |
| Notifications | ❌ No | ✅ Email/Slack |
| Rollback | ❌ Manual | ✅ 1 click |

---

## 🎯 Recomendación

- **Ahora/Demo**: Usa `deploy.sh`
- **Post-demo**: Configura GitHub Actions (2 min)

El archivo del workflow ya está en `.github/workflows/deploy.yml`
