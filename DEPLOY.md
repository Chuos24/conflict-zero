# CI/CD - Conflict Zero

## Opción 1: Deploy Manual (Recomendado para ahora)

```bash
cd /root/.openclaw/workspace/conflict-zero
./deploy.sh "mensaje del commit"
```

**Ventajas:**
- Funciona ahora mismo
- Control total del momento de deploy
- Feedback inmediato en terminal

---

## Opción 2: GitHub Actions (Largo plazo)

### Configuración paso a paso:

1. **Ve a tu repo en GitHub:**
   https://github.com/Chuos24/conflict-zero

2. **Crea el directorio:**
   ```
   Create new file → .github/workflows/deploy.yml
   ```

3. **Pega este contenido:**
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

4. **Configura el secret:**
   - Settings → Secrets and variables → Actions
   - New repository secret
   - Name: `RENDER_API_KEY`
   - Value: `rnd_TD2zaOUFhKiLOcvk5qQJNqxqAMKE`

5. **Listo!** Ahora cada push a `main` deploya automáticamente.

---

## Comparativa

| Feature | deploy.sh | GitHub Actions |
|---------|-----------|----------------|
| Setup | ✅ Listo | ⚠️ Requiere config |
| Control | ✅ Manual | ⚠️ Automático |
| Tests previos | ❌ No | ✅ Sí |
| Notificaciones | ❌ No | ✅ Sí |
| Equipo | ❌ 1 persona | ✅ Multi-user |
| Largo plazo | ⚠️ Limitado | ✅ Escalable |

---

## Recomendación

**Ahora:** Usa `./deploy.sh` (ya funciona)

**Cuando tengas 10 min:** Configura GitHub Actions para CI/CD profesional

**Render Service ID:** `srv-d6vagtfafjfc73cu0kdg`
**Render API Key:** Guardado en `.env.infrastructure`
