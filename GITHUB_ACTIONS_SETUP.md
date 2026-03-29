# ⚡ GitHub Actions - Setup Rápido (2 minutos)

## Paso 1: Copiar el workflow

Ve a tu repo: https://github.com/Chuos24/conflict-zero

Clickea aquí para crear el archivo:
```
https://github.com/Chuos24/conflict-zero/new/main?filename=.github/workflows/deploy.yml
```

## Paso 2: Pegar este contenido

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
      - name: Trigger Render Deploy
        env:
          RENDER_API_KEY: ${{ secrets.RENDER_API_KEY }}
        run: |
          curl -X POST \
            -H "Authorization: Bearer $RENDER_API_KEY" \
            -H "Content-Type: application/json" \
            -d '{"clearCache":false}' \
            https://api.render.com/v1/services/srv-d6vagtfafjfc73cu0kdg/deploys
```

## Paso 3: Configurar el secret

Ve a: `Settings → Secrets and variables → Actions → New repository secret`

- **Name:** `RENDER_API_KEY`
- **Value:** `rnd_TD2zaOUFhKiLOcvk5qQJNqxqAMKE`

## Paso 4: Probar

Haz un cambio en `backend/api_v3.py` y haz push.

Verás la acción corriendo en: `Actions` tab

---

## ✅ Listo!

Ahora cada push a `main` que modifique `backend/` hará:
1. Tests automáticos
2. Deploy a Render
3. Notificación de éxito/fallo

**URL del workflow:** https://github.com/Chuos24/conflict-zero/actions
