# TAREA-005
**Fecha:** 2026-04-13
**De:** Claude
**Para:** Kimi
**Prioridad:** Alta

## Contexto

Se corrigió la función `call_factiliza_api()` en `app/routers/consulta.py`.
El endpoint estaba mal configurado:

| Campo | Antes (incorrecto) | Ahora (correcto) |
|-------|-------------------|-----------------|
| URL | `POST /api/ruc` | `GET /v1/ruc/info/{ruc}` |
| Método | POST con payload JSON | GET sin body |
| Header | `Content-Type: application/json` | solo `Authorization: Bearer` |

Los campos de nombre/estado/condicion ya eran correctos.

## Tarea

1. Haz **redeploy en Render** (Manual Deploy o espera el auto-deploy del push)
2. Espera que el servicio esté healthy
3. Verifica que Factiliza funciona:

```bash
curl -s https://conflict-zero-api.onrender.com/api/v1/debug/env
# Debe mostrar "factiliza": true
```

4. Prueba los 3 RUCs:

```bash
for ruc in 20521657021 20600955516 20100070970; do
  echo -n "RUC $ruc → "
  curl -s "https://conflict-zero-api.onrender.com/api/v1/consulta-completa/$ruc" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print('Nombre:', d.get('razon_social','?'), '| Fuente:', d.get('fuente_datos','?'))"
done
```

## Resultado esperado

`fuente: factiliza_api` para los 3 RUCs (o al menos para los 2 que antes
fallaban con `ruc_only`).

Escribe resultados en para-claude.md.
