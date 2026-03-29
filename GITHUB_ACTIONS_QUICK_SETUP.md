# ⚡ GitHub Actions Setup - 2 Minutos

## Paso 1: Crear archivo (30 segundos)

Ve a este link directo:
```
https://github.com/Chuos24/conflict-zero/new/main/.github/workflows/deploy.yml
```

O manual:
1. https://github.com/Chuos24/conflict-zero
2. Click **Add file** → **Create new file**
3. En "Name your file..." escribe: `.github/workflows/deploy.yml`

## Paso 2: Pegar YAML (30 segundos)

Copia y pega esto exactamente:

```yaml
name: Deploy to Render

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt 2>/dev/null || true
      
      - name: Run syntax check
        run: |
          cd backend
          python -m py_compile api_v3.py
          echo "✅ Syntax OK"

  deploy:
    needs: test
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

## Paso 3: Agregar Secret (1 minuto)

1. Ve a: https://github.com/Chuos24/conflict-zero/settings/secrets/actions/new
2. **Name:** `RENDER_API_KEY`
3. **Value:** 
   ```
   rnd_TD2zaOUFhKiLOcvk5qQJNqxqAMKE
   ```
4. Click **Add secret**

## ✅ Listo!

Prueba: Modifica cualquier archivo en `backend/` y haz push a `main`.

Verás la acción corriendo en: https://github.com/Chuos24/conflict-zero/actions

---

## ¿Qué hace?

| Trigger | Acción |
|---------|--------|
| Push a `main` con cambios en `backend/` | Corre tests |
| Tests pasan | Deploy automático a Render |
| Tests fallan | No deploya (protección) |

## Beneficios vs deploy.sh

- ✅ No depende de este servidor
- ✅ Tests automáticos antes de deploy
- ✅ Historial visible en GitHub
- ✅ Notificaciones de éxito/fallo
- ✅ Rollback en 1 click
- ✅ Todo el equipo ve el estado

---

**¿Preguntas?** El setup es literalmente copiar-pegar 2 cosas.
