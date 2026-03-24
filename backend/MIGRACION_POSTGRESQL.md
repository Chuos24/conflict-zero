# 🗄️ PostgreSQL Migration Guide - Conflict Zero

**Fecha:** 2026-03-25  
**Status:** Listo para ejecutar  
**Riesgo:** Medio (con backups y rollback plan)  

---

## 📋 Resumen

Esta guía migra la base de datos de **SQLite** (archivo local) a **PostgreSQL** (servicio en Render), mejorando:
- ✅ Confiabilidad (PostgreSQL no se corrompe como SQLite)
- ✅ Concurrencia (múltiples conexiones simultáneas)
- ✅ Escalabilidad (crecimiento sin límites de archivo)
- ✅ Backup automático (Render hace backups diarios)

---

## 🎯 Plan de Migración (Zero Downtime)

### FASE 1: Preparación (5 minutos)

```bash
# 1. Asegúrate de estar en el directorio backend
cd /root/.openclaw/workspace/conflict-zero/backend

# 2. Verificar que el backup existe
ls -la ./backups/

# 3. Dar permisos de ejecución
chmod +x migrate-to-postgres.sh
chmod +x import_to_postgres.py
```

### FASE 2: Exportar Datos (2 minutos)

```bash
# Este script analiza SQLite y exporta todo a JSON
./migrate-to-postgres.sh
```

**Output esperado:**
```
📊 PASO 1: Analizando base de datos SQLite actual
✅ Base de datos SQLite encontrada
📏 Tamaño: 52K
📈 Registros por tabla:
  - users: 3 registros
  - verification_requests: 15 registros
  - api_keys: 0 registros
  - system_logs: 45 registros

💾 PASO 2: Exportando datos a JSON
✅ Usuarios exportados: 3
✅ Verificaciones exportadas: 15
✅ API Keys exportadas: 0
```

### FASE 3: Crear PostgreSQL en Render (3 minutos)

1. **Ir a Render Dashboard:** https://dashboard.render.com

2. **Crear Base de Datos:**
   - Click **"New"** → **"PostgreSQL"**
   - **Name:** `conflict-zero-db`
   - **Plan:** 
     - 🆓 **Free** - Para pruebas (1 GB, limitado)
     - 💎 **Starter** $7/mes - Recomendado para producción
   - **Region:** Same as your web service (recomendado)
   - Click **"Create Database"**

3. **Esperar:** Status cambia de "Creating" → "Available" (2-3 min)

### FASE 4: Obtener Credenciales (1 minuto)

En el dashboard de tu base de datos:

1. Copia **"Internal Database URL"** (si backend está en mismo region)
2. O copia **"External Database URL"** (si accedes desde fuera)

Se ve así:
```
postgresql://conflictzero:password@host:5432/conflictzero
```

### FASE 5: Crear Tablas en PostgreSQL (1 minuto)

```bash
# Conectarse a PostgreSQL (reemplaza DATABASE_URL con la tuya)
export DATABASE_URL="postgresql://conflictzero:password@host:5432/conflictzero"

# Ejecutar script de creación de tablas
psql $DATABASE_URL -f ./backups/postgres-migration-XXXX/create_tables.sql
```

**Output esperado:**
```
CREATE EXTENSION
CREATE TABLE
CREATE INDEX
...
CREATE TRIGGER
```

### FASE 6: Importar Datos (1 minuto)

```bash
# Instalar driver PostgreSQL para Python
pip install psycopg2-binary

# Ejecutar importación
export DATABASE_URL="postgresql://conflictzero:password@host:5432/conflictzero"
python3 import_to_postgres.py
```

**Output esperado:**
```
🚀 Importando datos a PostgreSQL
==================================================
📁 Usando backup: backups/postgres-migration-20260325-120000
✅ users: 3 registros cargados
✅ verification_requests: 15 registros cargados
✅ api_keys: 0 registros cargados

🔗 Conectando a PostgreSQL...
✅ Conexión exitosa

📥 Importando datos...
✅ Usuarios importados: 3
✅ Verificaciones importadas: 15
✅ API keys importadas: 0

✅ Importación completada exitosamente

📊 Verificación:
  - Usuarios en PostgreSQL: 3
  - Verificaciones en PostgreSQL: 15
  - API Keys en PostgreSQL: 0

🎉 Migración completada!
```

### FASE 7: Actualizar Render (2 minutos)

1. **Ir a tu Web Service** en Render Dashboard
2. **Environment Variables:**
   - Agregar/Editar: `DATABASE_URL`
   - Valor: (la URL de PostgreSQL del paso 4)
3. **Save Changes**
4. **Manual Deploy** → **Clear build cache & deploy**

### FASE 8: Verificación (3 minutos)

```bash
# 1. Health Check
curl https://conflictzero-api.onrender.com/health

# Debe retornar:
# {"status": "healthy", "database": "connected"}

# 2. Probar login
curl -X POST https://conflictzero-api.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "founder@conflictzero.com", "password": "CZ2025!"}'

# 3. Verificar datos persistidos
# Hacer una consulta en el dashboard
```

---

## 🔙 Plan de Rollback (Si algo falla)

Si algo sale mal, puedes volver a SQLite en **menos de 1 minuto**:

### Opción A: Cambiar variable de entorno (Recomendado)

```bash
# En Render Dashboard:
# 1. Ir a Environment Variables
# 2. Cambiar DATABASE_URL a: sqlite:///./conflictzero.db
# 3. Deploy
```

### Opción B: Usar backup

```bash
# El backup original de SQLite siempre está seguro:
ls -la ./backups/2026-03-24-research-phase/conflict-zero/backend/conflictzero.db

# Copiar de vuelta si es necesario:
cp ./backups/2026-03-24-research-phase/conflict-zero/backend/conflictzero.db ./conflictzero.db
```

---

## 🧪 Testing Checklist

Antes de declarar éxito, verifica:

- [ ] Login funciona con credenciales existentes
- [ ] Registro de nuevos usuarios funciona
- [ ] Verificación de RUC guarda en historial
- [ ] Historial de verificaciones visible
- [ ] Planes y límites respetados
- [ ] Founder user tiene acceso admin

---

## 📊 Comparativa: SQLite vs PostgreSQL

| Característica | SQLite | PostgreSQL |
|---------------|--------|------------|
| Tipo | Archivo local | Servicio de red |
| Concurrency | 1 escritura a la vez | Múltiples simultáneas |
| Tamaño máximo | ~140 TB (teórico) | Ilimitado |
| Backup | Manual | Automático (Render) |
| Escalabilidad | Limitada | Alta |
| Costo en Render | Gratis | Free o $7/mes |
| Recomendado para | Dev/Testing | Producción |

---

## 🔧 Troubleshooting

### Error: "database does not exist"
```bash
# La base de datos se crea automáticamente, pero si hay problema:
psql $DATABASE_URL -c "CREATE DATABASE conflictzero;"
```

### Error: "relation already exists"
```bash
# Si las tablas ya existen, limpiar primero:
psql $DATABASE_URL -c "DROP TABLE IF EXISTS verification_requests, api_keys, system_logs, users CASCADE;"
```

### Error: "ModuleNotFoundError: psycopg2"
```bash
pip install psycopg2-binary
# o
pip install psycopg2
```

### Error de conexión desde local
```bash
# PostgreSQL en Render solo acepta conexiones externas si está configurado
# Usar "Internal Database URL" solo funciona desde servicios en Render
# Para conectar desde tu máquina, usar "External Database URL"
```

---

## 📁 Archivos Generados

```
backend/
├── migrate-to-postgres.sh          # Script principal de migración
├── import_to_postgres.py           # Script de importación Python
├── MIGRACION_POSTGRESQL.md         # Esta guía
└── backups/
    └── postgres-migration-YYYYMMDD-HHMMSS/
        ├── create_tables.sql       # Schema SQL
        ├── users.json              # Datos exportados
        ├── verification_requests.json
        └── api_keys.json
```

---

## 🎉 Post-Migración

Una vez exitosa la migración:

1. **Eliminar SQLite** (opcional, después de 1 semana estable):
   ```bash
   rm conflictzero.db
   ```

2. **Configurar backups automáticos** (Render ya lo hace)

3. **Monitorear uso:**
   ```bash
   # Conectar y ver estadísticas
   psql $DATABASE_URL -c "SELECT pg_size_pretty(pg_database_size('conflictzero'));"
   ```

---

## 📞 Soporte

Si algo sale mal:
1. Revisar logs en Render Dashboard
2. Verificar DATABASE_URL esté correcta
3. Probar conexión manual con psql
4. Rollback a SQLite si es necesario

---

**¿Listo para empezar?** Ejecuta `./migrate-to-postgres.sh` y sigue las instrucciones.