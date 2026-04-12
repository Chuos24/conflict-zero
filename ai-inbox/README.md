# AI-Inbox System

Sistema de coordinación automática entre Claude Code (Mac) y Kimi Claw (VPS).

## Cómo funciona

### Flujo de trabajo:

1. **Claude Code** escribe instrucciones en `para-kimi.md`
2. **Kimi Claw** (cron cada hora):
   - Hace `git pull`
   - Lee `para-kimi.md`
   - Ejecuta las instrucciones
   - Escribe resultado en `para-claude.md`
   - Hace `git push`
3. **Claude Code** lee `para-claude.md` en su siguiente sesión

## Archivos

| Archivo | Quién escribe | Quién lee |
|---------|---------------|-----------|
| `para-kimi.md` | Claude | Kimi |
| `para-claude.md` | Kimi | Claude |
| `historial/` | Auto | Ambos |

## Formato de instrucciones

```markdown
# Instrucciones para Kimi
**Fecha:** 2026-04-13
**Prioridad:** Alta/Media/Baja

## Tarea
[Descripción clara de qué hacer]

## Comandos (opcional)
```bash
# Comandos específicos para ejecutar
comando1
comando2
```

## Notas
[Cualquier contexto adicional]
```

## Ejemplo de uso

### Claude escribe:
```markdown
# Para Kimi

Verifica si el deploy de ayer funcionó:
- Revisa https://czperu.com/api/health
- Si hay errores, intenta reiniciar el servicio
- Documenta lo que encuentres
```

### Kimi responde (~1 hora después):
```markdown
# Respuesta de Kimi Claw
**Fecha:** 2026-04-13 14:00:00
**Estado:** Completado

## Resultado:
✅ Health check: OK
✅ Deploy funcionando correctamente
```

## Limitaciones actuales

- Kimi ejecuta instrucciones manualmente (no automatizado aún)
- El cron job actual solo archiva y responde
- Futuro: parsear comandos y ejecutar automáticamente

## Cron Job

```bash
# Ejecuta cada hora en punto
0 * * * * /root/.openclaw/workspace/ai-inbox-bridge.sh
```

Logs: `/var/log/ai-inbox-cron.log`
