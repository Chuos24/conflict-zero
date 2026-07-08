# Conflict Zero — 4 Fixes Completos (Código Listo para Copiar-Pegar)

> Commit: `c204265` | 2026-05-02
> Si Render no auto-deploya, copia estos snippets directo a los archivos locales.

---

## 1. FIX CRÍTICO — Migración DB: `init_database()` en `app/main.py`

**Ubicación:** Reemplaza la función `init_database()` existente en `app/main.py` (línea ~52)

```python
# Crear tablas y migrar columnas faltantes (con manejo de errores para no bloquear startup)
def init_database():
    try:
        from sqlalchemy import inspect, text
        from app.models import Invitation
        
        # 1. Crear tablas que no existen
        Base.metadata.create_all(bind=engine)
        
        # 2. Migrar columnas faltantes en tablas existentes (PostgreSQL-safe)
        inspector = inspect(engine)
        
        # --- invitations table ---
        if inspector.has_table("invitations"):
            existing_cols = {c["name"] for c in inspector.get_columns("invitations")}
            required_cols = {
                "name": "VARCHAR(255)",
                "company": "VARCHAR(255)",
                "notes": "TEXT",
                "accepted_by": "VARCHAR(36)"
            }
            with engine.connect() as conn:
                for col_name, col_type in required_cols.items():
                    if col_name not in existing_cols:
                        conn.execute(text(f'ALTER TABLE invitations ADD COLUMN IF NOT EXISTS {col_name} {col_type}'))
                        conn.commit()
                        print(f"✅ Columna '{col_name}' agregada a invitations")
        
        print("✅ Base de datos lista")
        return True
    except Exception as e:
        print(f"⚠️ Error conectando a base de datos: {e}")
        return False
```

**También agregar este endpoint en `app/routers/admin.py`** (después de `admin_root()`):

```python
@router.post("/migrate-db")
async def migrate_db(authorization: str = Header(None), db: Session = Depends(get_db)):
    """Ejecuta migración manual de columnas faltantes. Útil cuando auto-migrate falla."""
    if not _require_admin(authorization):
        return JSONResponse(status_code=401, content={'success': False, 'error': 'UNAUTHORIZED'})
    
    from sqlalchemy import inspect, text
    from app.core.database import engine
    
    results = []
    try:
        inspector = inspect(engine)
        
        if inspector.has_table("invitations"):
            existing_cols = {c["name"] for c in inspector.get_columns("invitations")}
            required_cols = {
                "name": "VARCHAR(255)",
                "company": "VARCHAR(255)",
                "notes": "TEXT",
                "accepted_by": "VARCHAR(36)"
            }
            with engine.connect() as conn:
                for col_name, col_type in required_cols.items():
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f'ALTER TABLE invitations ADD COLUMN IF NOT EXISTS {col_name} {col_type}'))
                            conn.commit()
                            results.append({"table": "invitations", "column": col_name, "status": "created"})
                        except Exception as e:
                            results.append({"table": "invitations", "column": col_name, "status": "error", "error": str(e)})
                    else:
                        results.append({"table": "invitations", "column": col_name, "status": "already_exists"})
        else:
            results.append({"table": "invitations", "status": "table_not_found"})
        
        return {"success": True, "migrations": results}
    except Exception as e:
        return JSONResponse(status_code=500, content={'success': False, 'error': str(e), 'migrations': results})
```

**Y actualizar `admin_root()` para listar el nuevo endpoint:**

```python
@router.get("/")
async def admin_root():
    """Root endpoint - info básica"""
    return {"message": "Admin API - Payment System v1.0", "endpoints": [
        "/record-payment",
        "/activate-plan", 
        "/pending-activations",
        "/payments-history",
        "/migrate-db"
    ]}
```

---

## 2. FIX CRÍTICO — Validación RUC Inválido: `app/routers/consulta.py`

**Ubicación:** Dentro de `consulta_completa()`, después de `sunat_data = get_sunat_data_cascade(ruc, db)` y antes de consultar sanciones.

```python
    # Use cleaned cascade: Factaliza → APIPeru.dev → Perú API → apis.net.pe → DB fallback
    sunat_data = get_sunat_data_cascade(ruc, db)
    
    # FIX CRÍTICO: Rechazar RUCs inválidos (ninguna fuente real devolvió datos)
    es_ruc_real = bool(sunat_data.get("razon_social", "").strip()) and sunat_data.get("fuente") != "minimal_fallback"
    if not es_ruc_real:
        return {
            "ruc": ruc,
            "razon_social": sunat_data.get("razon_social", "No disponible"),
            "estado": "DESCONOCIDO",
            "condicion": "DESCONOCIDO",
            "score": 15,
            "risk_level": "RECHAZADO",
            "risk_emoji": "⛔",
            "risk_description": "RUC no verificable o empresa inexistente en registros oficiales",
            "sunat": {
                "ruc": ruc,
                "razon_social": "No disponible",
                "estado": "DESCONOCIDO",
                "condicion": "DESCONOCIDO",
                "direccion": ""
            },
            "sanciones": [],
            "sanciones_osce": [],
            "sanciones_rnp_tce": [],
            "total_registros": 0,
            "fuentes": {
                "sunat": False,
                "osce": 0,
                "rnp_tce": 0
            },
            "score_breakdown": {
                "sunat": 0,
                "osce": 0,
                "tce": 0,
                "ml": 0
            },
            "score_details": {
                "sunat_score": 0,
                "osce_score": 0,
                "tce_score": 0,
                "ml_score": 0
            },
            "fuente_datos": sunat_data.get("fuente", "unknown"),
            "ml_analysis": {
                "risk_detected": True,
                "risk_factors": ["RUC no encontrado en fuentes oficiales"],
                "confidence": 1.0
            },
            "valid": False
        }
    
    # Consultar sanciones OSCE (datos reales de CONOSCE)
    osce_sanciones = scraping_service.get_osce_sanctions(ruc)
```

---

## 3. FIX MEDIO — Health Endpoint v3: `app/main.py`

**Ubicación:** En la sección "Routers v3" (línea ~190), agregar `health_router`:

```python
# Routers v3 (para compatibilidad con frontend)
app.include_router(auth_router, prefix="/api/v3")
app.include_router(verification_router, prefix="/api/v3")
app.include_router(consulta_router, prefix="/api/v3")
app.include_router(dashboard_router, prefix="/api/v3")
app.include_router(compare_router, prefix="/api/v3")
app.include_router(payments_router, prefix="/api/v3")
app.include_router(payments_v2_router, prefix="/api/v3")
app.include_router(admin_router, prefix="/api/v3")
app.include_router(notifications_router, prefix="/api/v3")
app.include_router(health_router, prefix="/api/v3")  # FIX: Health disponible en v3
```

**También actualizar el rate limit whitelist** (línea ~160):

```python
    if request.url.path in ["/api/v1/health", "/api/v3/health", "/docs", "/redoc", "/openapi.json"]:
        return await call_next(request)
```

---

## 4. FIX MEDIO — Network/{ruc}: `app/routers/network.py`

**Ubicación:** Agregar después de `network_stats()` y antes de `list_watchlist()`.

```python
@router.get("/{ruc}")
async def get_network_ruc(
    ruc: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Obtiene los datos de un proveedor específico en la red del usuario.
    """
    _require_pro(current_user)

    if len(ruc) != 11 or not ruc.isdigit():
        raise HTTPException(status_code=400, detail="RUC debe tener 11 dígitos numéricos.")

    entry = (
        db.query(NetworkWatchlist)
        .filter(
            NetworkWatchlist.user_id == current_user.id,
            NetworkWatchlist.ruc == ruc,
        )
        .first()
    )

    if not entry:
        raise HTTPException(status_code=404, detail="RUC no encontrado en tu red.")

    # Verificar si hay alertas pendientes
    has_pending = db.query(NetworkAlert).filter(
        NetworkAlert.user_id == current_user.id,
        NetworkAlert.ruc == ruc,
        NetworkAlert.read_at == None,
    ).first() is not None

    return {
        "success": True,
        "supplier": {
            "id": entry.id,
            "ruc": entry.ruc,
            "alias": entry.alias,
            "last_score": entry.last_score,
            "last_status": entry.last_status,
            "has_pending_alerts": has_pending,
            "created_at": entry.created_at.isoformat() if entry.created_at else None,
        }
    }
```

---

## Diagnóstico Render (si auto-deploy no funciona)

El commit `c204265` está en `origin/main`. Si Render no deploya automáticamente:

1. **Verifica branch en Render Dashboard** → Settings → Build & Deploy → Branch name = `main`
2. **Verifica auto-deploy** → Settings → Auto-Deploy = ON
3. **Forzar deploy manual** → Dashboard → Manual Deploy → Deploy latest commit
4. **Verificar logs** → Dashboard → Logs (buscar errores de build)

**Alternativa manual:** El usuario puede pushear desde su terminal:
```bash
cd /Users/santi/conflictzero  # o donde tenga el repo
# Aplicar los snippets de arriba
# Luego:
git add -A
git commit -m "fix: 4 critical fixes - db migrate, ruc validation, health v3, network/ruc"
git push origin main
```

Si el problema es que Render monitorea otro repo/branch, el usuario puede crear un deploy hook manual desde el dashboard.
