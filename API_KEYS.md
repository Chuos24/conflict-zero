# API Keys Configuradas

## Perú API (Primaria)
TOKEN: d02bb5a71984e759885a4e47a575715c
Estado: ✅ Configurada

## Decolecta (Fallback)
TOKEN: sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU
Estado: ✅ Configurada

---

## Flujo de Datos

1. **Intenta Perú API primero** (más rápida, plan free)
2. **Si falla → Intenta Decolecta** (backup pago)
3. **Si ambas fallan → Error 503** (nunca datos falsos)

## Seguridad

⚠️ **NUNCA subir este archivo a GitHub**

Las keys están en:
- AWS Lambda (seguro)
- AWS Secrets Manager (seguro)
- Archivos .env locales (nunca en git)
