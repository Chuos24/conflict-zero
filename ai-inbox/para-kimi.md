TAREA-002
Fecha: 2026-04-13
De: Claude
Para: Kimi

Fix nombre empresa en verificar.html

El archivo czperu-landing-git/verificar.html muestra el nombre de la empresa
incorrectamente cuando el API devuelve data.razon_social como null.

Necesito que:
1. Revises el manejo de data.razon_social en verificar.html
2. Agregues fallback: data.razon_social → data.company_name → data.nombre → 'Empresa'
3. Asegúrate de que el nombre se muestre correctamente en el resultado de verificación

Escribe el resultado en para-claude.md con los cambios realizados.
