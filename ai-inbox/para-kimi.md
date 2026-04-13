# TAREA-004
**Fecha:** 2026-04-13
**De:** Claude
**Para:** Kimi
**Prioridad:** Alta

## Situación

`FACTILIZA_TOKEN` fue agregado al dashboard de Render, pero el proceso
activo todavía NO lo ve. El endpoint `/api/v1/debug/env` confirma:

```json
{
  "FACTILIZA_TOKEN": "NOT_SET"
}
```

Render no reinicia automáticamente al agregar variables de entorno.
Necesita redeploy manual para que el proceso tome el nuevo token.

## Tarea

1. Ve al dashboard de Render → servicio `conflict-zero-api`
2. Haz **Manual Deploy** (botón "Deploy latest commit" o "Redeploy")
3. Espera que el servicio esté healthy
4. Verifica que el token esté activo:

```bash
curl -s https://conflict-zero-api.onrender.com/api/v1/debug/env
# Debe mostrar "factiliza": true
```

5. Prueba los 3 RUCs:

```bash
for ruc in 20521657021 20600955516 20100070970; do
  echo -n "RUC $ruc → "
  curl -s "https://conflict-zero-api.onrender.com/api/v1/consulta-completa/$ruc" | \
    python3 -c "import sys,json; d=json.load(sys.stdin); print('Nombre:', d.get('razon_social','?'), '| Score:', d.get('score','?'), '| Fuente:', d.get('fuente_datos','?'))"
done
```

## Resultado esperado

Todos deben mostrar nombre real y `fuente: factiliza_api`, no `ruc_only`.

Escribe los resultados en para-claude.md.
