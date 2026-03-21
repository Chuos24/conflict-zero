# 🚨 GUÍA RÁPIDA - CONFLICT ZERO FUNCIONANDO

## Estado Actual

El backend está desplegado pero necesita:
1. **Redeploy forzado** para aplicar últimos cambios
2. **Creación manual del usuario founder**

---

## 🎯 Instrucciones para hacer AHORA (5 minutos)

### 1. Forzar Redeploy en Render
```
https://dashboard.render.com/ → conflict-zero-api → Settings 
→ Clear build cache & deploy
```

### 2. Crear Usuario Founder
Una vez que termine el deploy (estado "Live"), abre en navegador:
```
https://conflict-zero-api.onrender.com/api/v1/auth/setup/create-founder
```

Debería mostrar:
```json
{
  "message": "Usuario founder creado exitosamente",
  "email": "founder@conflictzero.com",
  "password": "FounderPass2025!"
}
```

### 3. Probar Login
Ve a tu frontend de Netlify e intenta login con:
- **Email**: `founder@conflictzero.com`
- **Password**: `FounderPass2025!`

---

## 🔧 Si el Paso 2 falla (404)

El deploy no se completó correctamente. Repite el paso 1 y espera 5 minutos.

---

## 🔧 Si el Paso 3 falla (401)

El usuario no se creó. Usa el registro normal:
1. Ve a tu frontend de Netlify
2. Click en "Registrarse"
3. Crea una cuenta nueva con cualquier email
4. Eso funcionará inmediatamente

---

## 📱 URLs Importantes

| Servicio | URL |
|----------|-----|
| Backend | https://conflict-zero-api.onrender.com |
| Frontend | (tu URL de Netlify) |
| Health Check | https://conflict-zero-api.onrender.com/health |
| Crear Founder | https://conflict-zero-api.onrender.com/api/v1/auth/setup/create-founder |

---

## ✅ Checklist Final

- [ ] Redeploy completado en Render (estado "Live")
- [ ] Endpoint de founder responde 200 OK
- [ ] Login funciona con founder@conflictzero.com
- [ ] Frontend de Netlify carga correctamente

---

**Todo está listo. Solo necesitas hacer el redeploy y crear el usuario founder.**

Buenas noches! 🌙
