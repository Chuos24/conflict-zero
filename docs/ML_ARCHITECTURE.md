# Arquitectura ML-Ready: Conflict Zero

**Fecha:** 2026-03-28  
**Estado:** Implementado ✅ | **ML Activo:** Mes 3-6 (cuando datos > 1000 filas)

---

## 🎯 Filosofía

> "Guardamos datos desde el día 1. Entrenamos cuando el jardín florezca."

**Hoy:** Guardamos time-series de cada consulta sin que el usuario lo note.  
**Mañana:** Entrenamos modelo predictivo con 6 meses de datos históricos.

---

## 🏗️ Componentes

### 1. Company Snapshots (Time-Series)

Cada vez que alguien consulta un RUC, guardamos:

```sql
CREATE TABLE company_snapshots (
    id UUID PRIMARY KEY,
    ruc VARCHAR(11),
    snapshot_date TIMESTAMP,  -- Cuándo
    
    -- Datos SUNAT (time-series)
    sunat_status,
    sunat_debt,
    sunat_num_trabajadores,
    
    -- Datos OSCE (time-series)
    osce_inhabilitado,
    osce_sanciones_count,
    osce_sanciones_vigentes,
    
    -- Features para ML
    dias_ultimo_pago,         -- Feature: morosidad temporal
    dias_ultima_sancion,      -- Feature: recurrencia de sanciones
    score_calculado           -- Target para ML
);
```

**Índice crítico:** `(ruc, snapshot_date)` para consultas time-series rápidas.

### 2. Snapshot Service

```python
# Cada verificación automáticamente guarda snapshot
snapshot_service.save_snapshot(
    ruc="20100123091",
    sunat_data={...},
    osce_data={...},
    score_data={...}
)
```

**Detección de cambios:** Compara con snapshot anterior y detecta:
- `osce_inhabilitado` (pasó de False → True)
- `nueva_sancion` (apareció sanción vigente)
- `nueva_deuda` (apareció deuda SUNAT)

### 3. Supplier Alerts (Valor inmediato)

Cuando un proveedor de un cliente Gold cambia de estado:

```sql
CREATE TABLE supplier_alerts (
    user_id,           -- A quién alertar
    supplier_ruc,      -- Qué proveedor
    change_type,       -- 'osce_inhabilitado', etc.
    severity,          -- low/medium/high/critical
    is_read
);
```

**Flujo:**
1. Cliente Gold consulta proveedor X
2. Sistema guarda snapshot
3. Detecta cambio respecto a consulta anterior
4. Crea alerta si es high/critical
5. Envía email: "⚠️ Su proveedor X fue inhabilitado por OSCE"

**Esto NO es ML, es detección de cambio. Pero es valor real inmediato.**

### 4. Data Lake (CSV Semanal)

```bash
# Cron job semanal
0 2 * * 0 python scripts/export_snapshots_to_csv.py --weeks 4
```

Genera: `data/company_snapshots_2026_w12.csv`

**Estructura CSV:**
```csv
ruc,snapshot_date,sunat_debt,osce_sanciones_vigentes,dias_ultimo_pago,score_calculado
20100123091,2026-03-28T10:00:00,0.0,2,45,75
...
```

Cuando tengamos 6 meses de CSVs → Dataset ML listo.

### 5. ML Training Log (Placeholder)

```sql
CREATE TABLE ml_training_logs (
    model_version,
    training_date,
    dataset_size,      -- Cuántos snapshots usamos
    accuracy,
    precision,
    recall,
    is_active          -- Este modelo está en producción?
);
```

**Ahora:** Vacío (guardamos datos, no entrenamos).  
**Mes 3-6:** Primeros entrenamientos con 1000+ snapshots.

---

## 🔄 Flujo de Datos

```
Consulta RUC
    ↓
[SnapshotService] → Guarda en PostgreSQL (company_snapshots)
    ↓
[Detect Changes] → ¿Cambió respecto a anterior?
    ↓ Sí
[Crear Alerta] → supplier_alerts (si es cliente Gold)
    ↓
[Email] → "Su proveedor X cambió de estado"
    ↓
[Cron Semanal] → Exporta a CSV
    ↓
[Mes 3-6] → Entrenar modelo con CSVs acumulados
    ↓
[Deploy] → Modelo ML en producción (predictivo)
```

---

## 📊 Queries para ML (Futuro)

```sql
-- "Empresas sanas hace 3 meses, inhabilitadas hoy"
-- Esto será nuestro training set positivo
SELECT ruc 
FROM company_snapshots 
WHERE snapshot_date > NOW() - INTERVAL '3 months'
  AND osce_inhabilitado = TRUE;

-- Evolución temporal de una empresa
SELECT * FROM company_snapshots 
WHERE ruc = '20100123091' 
ORDER BY snapshot_date;

-- Features para modelo
SELECT 
    ruc,
    AVG(dias_ultimo_pago) as avg_morosidad,
    COUNT(CASE WHEN osce_sanciones_vigentes > 0 THEN 1 END) as meses_con_sanciones,
    MAX(osce_sanciones_vigentes) as max_sanciones_simultaneas
FROM company_snapshots 
GROUP BY ruc;
```

---

## 🚀 Roadmap ML

| Fase | Tiempo | Acción |
|------|--------|--------|
| **Fase 0** | Ahora | Guardar snapshots (hecho ✅) |
| **Fase 1** | Semana 2 | Alertas automáticas de cambios |
| **Fase 2** | Mes 3 | Primer dataset CSV (12 semanas) |
| **Fase 3** | Mes 4-6 | Entrenar modelo con 1000+ snapshots |
| **Fase 4** | Mes 6+ | Score predictivo en producción |

---

## 💡 Ventaja Competitiva

**En 6 meses tendremos:**
- Dataset único: Evolución temporal de miles de empresas peruanas
- Modelo entrenado: Predice riesgo antes de que OSCE publique
- Barrera de entrada: Competidores nuevos no tienen historial

**Mientras tanto (hoy):**
- Clientes no notan nada diferente
- Pero estamos guardando TODO
- Alertas de cambio dan valor inmediato

---

## 🔧 Mantenimiento

```bash
# Aplicar migración
alembic upgrade head

# Exportar snapshots semanal (cron)
python scripts/export_snapshots_to_csv.py --weeks 4

# Ver estadísticas
curl https://api.conflictzero.com/api/v1/admin/snapshot-stats
```

---

**Nota:** Esta arquitectura no afecta la experiencia del usuario hoy.
Es invisible, pero en 6 meses será nuestro activo más valioso.
