# Configuración de API Keys - COMPLETO

## API Keys Configuradas

### Perú API (Primaria)
**Token:** `d02bb5a71984e759885a4e47a575715c`

### Decolecta (Fallback)
**Token:** `sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU`

---

## Paso 1: Configurar en AWS Lambda (URGENTE)

### Opción A: AWS Console (Web)
1. Ve a AWS Console → Lambda
2. Busca tu función `conflictzero-api` (o similar)
3. Click en "Configuration" → "Environment variables"
4. Click "Edit"
5. Agrega estas variables:

| Key | Value |
|-----|-------|
| `PERUAPI_TOKEN` | `d02bb5a71984e759885a4e47a575715c` |
| `DECOLECTA_API_KEY` | `sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU` |
| `S3_BUCKET` | `conflictzero-certificados-prod` |

6. Guardar

### Opción B: AWS CLI
```bash
aws lambda update-function-configuration \
  --function-name conflictzero-api \
  --environment "Variables={PERUAPI_TOKEN=d02bb5a71984e759885a4e47a575715c,DECOLECTA_API_KEY=sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU,S3_BUCKET=conflictzero-certificados-prod}"
```

---

## Paso 2: Configurar en Backend (si tienes backend separado)

### Si usas Docker/.env:
```bash
cd backend
cat >> .env << EOF
PERUAPI_TOKEN=d02bb5a71984e759885a4e47a575715c
DECOLECTA_API_KEY=sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU
EOF
```

### Si usas AWS ECS/Secrets Manager:
1. Ve a AWS Secrets Manager
2. Busca tu secret (ej: `conflictzero/prod`)
3. Agrega los keys:
```json
{
  "PERUAPI_TOKEN": "d02bb5a71984e759885a4e47a575715c",
  "DECOLECTA_API_KEY": "sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU",
  "DATABASE_URL": "...",
  "SECRET_KEY": "..."
}
```
4. Guardar

---

## Paso 3: Verificar Funcionamiento

### Test RUC Real (Interbank)
```bash
curl "https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod/consulta-osce/20100017491"
```

**Respuesta esperada:**
```json
{
  "success": true,
  "datos_reales": true,
  "data": {
    "ruc": "20100017491",
    "razon_social": "INTERBANK S.A.",
    "estado_sunat": "ACTIVO",
    "condicion": "HABIDO",
    "direccion": "JR. DOMINGO MARTINEZ LUJAN NRO. 1130",
    "departamento": "LIMA",
    "provincia": "LIMA",
    "distrito": "SURQUILLO",
    "fuentes_datos": {
      "sunat": "peruapi_sunat"
    }
  },
  "score": 85
}
```

Si ves `"razon_social": "INTERBANK S.A."` → ✅ **Funciona con datos reales**

---

## Sobre las dos APIs

| Aspecto | Perú API | Decolecta |
|---------|----------|-----------|
| **Rol** | Primaria | Fallback |
| **Plan** | Free (100/día) | Pago (ilimitado) |
| **Se usa** | Primero | Si Perú API falla |
| **Datos** | SUNAT real | SUNAT real |

**Flujo:**
1. Intenta Perú API primero
2. Si falla → Intenta Decolecta
3. Si ambas fallan → Error 503

---

## Monitoreo del Uso

### Perú API (Plan Free)
- 100 consultas/día
- 1,000 consultas/mes

**Para ver tu uso:**
1. Login en https://peruapi.com
2. Panel de control muestra consultas usadas

### Decolecta (Plan Pago)
- Consultas ilimitadas (según tu plan)
- Se usa solo si Perú API falla

---

## ⚠️ IMPORTANTE - Seguridad

**NO compartir estas API keys públicamente.**

Están configuradas en:
- ✅ AWS Lambda (seguro)
- ✅ AWS Secrets Manager (seguro)
- ✅ Tu archivo `.env` local (no subir a git)
- ❌ NUNCA en repositorio público

**Si una key se filtra:**
1. Ir al proveedor (peruapi.com o decolecta.com)
2. Rotar/regenerar el token
3. Actualizar en AWS Lambda inmediatamente

---

## Troubleshooting

### "No se pudieron obtener datos de SUNAT"
- Verificar que PERUAPI_TOKEN esté en Lambda
- Verificar que DECOLECTA_API_KEY esté en Lambda
- Revisar logs de CloudWatch

### "datos_reales": false
- Esto NO debe pasar con las APIs configuradas
- Verificar que las keys sean válidas
- Verificar que no haya espacios extra en las keys
