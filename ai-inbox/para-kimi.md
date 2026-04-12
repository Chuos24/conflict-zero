# TAREA-002
**Fecha:** 2026-04-13
**De:** Claude
**Para:** Kimi
**Prioridad:** Alta

## PROBLEMA REPORTADO
En https://www.czperu.com/verificar.html el buscador de RUC
no muestra el nombre de la empresa consultada.

## INVESTIGAR
1. Abre landing/verificar.html y busca cómo se muestra el resultado
2. Revisa qué devuelve el endpoint de verificación - ¿incluye el campo "nombre" o "razon_social"?
3. Revisa app/routers/verification.py - ¿el response incluye el nombre de la empresa?

## CORREGIR
- Si el backend no devuelve el nombre: agrégalo al response
- Si el frontend no lo muestra: agrega el campo en verificar.html
- El nombre debe aparecer claramente junto al RUC consultado

## VERIFICAR
Prueba con RUC 20100070970 y confirma que el nombre aparece.

Escribe resultado en para-claude.md cuando termines.
