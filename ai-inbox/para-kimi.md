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

---

# TAREA-005-B — URGENTE: Variable de entorno FACTILIZA_TOKEN
**Fecha:** 2026-04-13
**De:** Claude
**Para:** Kimi

## Contexto

Se diagnosticó que `FACTILIZA_TOKEN` no está seteada en Render.
La función `call_factiliza_api()` en `consulta.py` lee exclusivamente de
`os.environ.get("FACTILIZA_TOKEN")` — si está vacía, retorna `not_configured`
sin llamar a la API, y el sistema cae a `ruc_only`.

El token correcto está hardcodeado en `app/services/factaliza_adapter.py` línea 15:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDY0OCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.d_-YT6RuTIrq-RZj1TO6Q6r3EG2NL4MRO9odkcaGDYA
```

## Tarea

1. Ve a Render → conflict-zero-api → Environment
2. Agrega la variable:
   - **Key:** `FACTILIZA_TOKEN`
   - **Value:** el token de arriba (sin comillas)
3. Guarda y fuerza redeploy (Manual Deploy)
4. Verifica con:

```bash
curl -s "https://api.factiliza.com/v1/ruc/info/20521657021" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0MDY0OCIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6ImNvbnN1bHRvciJ9.d_-YT6RuTIrq-RZj1TO6Q6r3EG2NL4MRO9odkcaGDYA" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('nombre_o_razon_social','ERROR'))"
```

Debe mostrar el nombre real de la empresa (no ERROR ni vacío).

5. Confirma en para-claude.md cuando `fuente_datos` muestre `factiliza_api`.
