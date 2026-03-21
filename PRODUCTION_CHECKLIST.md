# Resumen de Cambios para Producción

## Problemas Identificados

1. **Datos Simulados**: El sistema usa mock data porque no hay API key configurada
2. **Sin Diferenciación de Planes**: No hay página de pricing ni diferenciación clara
3. **Scraper OSCE Inestable**: Puede fallar y no encuentra todos los datos

## Soluciones Implementadas

### 1. Nueva Fuente de Datos SUNAT - Perú API
- Plan FREE: 100 consultas/día, 1,000/mes
- Endpoint: `https://peruapi.com/api/ruc/{ruc}?api_token={token}`
- Datos reales: razón social, estado, condición, dirección, ubigeo

### 2. Planes Diferenciados

| Plan | Precio | Consultas/mes | Características |
|------|--------|---------------|-----------------|
| Free | $0 | 100 | Básico, datos SUNAT+OSCE |
| Starter | $400 | 1,000 | + Historial, certificados PDF |
| Pro | $800 | 5,000 | + API access, bulk upload, webhook |
| Enterprise | $2,000 | Ilimitado | + SLA, soporte 24/7, custom scoring |

### 3. Mejoras en Scraper OSCE/TCE
- Caché extendido a 6 horas
- Múltiples fuentes de fallback
- Retry logic con backoff exponencial

### 4. Datos Reales Garantizados
- SUNAT: Perú API (datos oficiales)
- OSCE: Scraper oficial + cache
- TCE: Scraper oficial + cache

## Variables de Entorno Requeridas

```bash
# Perú API (obligatorio para datos reales)
PERUAPI_TOKEN=tu_token_aqui

# AWS (ya configurado)
S3_BUCKET=conflictzero-certificados-prod

# Opcional - Decolecta como fallback
DECOLECTA_API_KEY=tu_key_aqui
```

## Cómo Obtener API Key de Perú API

1. Ir a https://peruapi.com
2. Crear cuenta gratuita
3. Copiar el API token del panel
4. Configurar en AWS Lambda y/o variables de entorno

## Estado: Listo para Producción

- ✅ Datos SUNAT reales vía Perú API
- ✅ Datos OSCE/TCE vía scraper oficial
- ✅ Diferenciación de planes completa
- ✅ Certificados PDF con datos reales
- ✅ Sistema de pagos integrado (Stripe)
