# 🚀 GUÍA COMPLETA DE DEPLOY - Conflict Zero

## 📋 RESUMEN

Vamos a deployar Conflict Zero en **3 pasos**:
1. Subir código a GitHub
2. Deployar Backend en Render (gratis)
3. Deployar Frontend en Netlify (gratis)

---

## PASO 1: Subir a GitHub

### 1.1 Crear Repositorio
- Ve a: https://github.com/new
- Nombre: `conflict-zero`
- Descripción: "Verificación predictiva de RUCs peruanos"
- Público o Privado (tú eliges)
- **NO** inicializar con README (ya tenemos uno)
- Click: **Create repository**

### 1.2 Subir Código
En tu terminal (en la carpeta del proyecto):

```bash
cd /root/.openclaw/workspace/conflict-zero

git init
git add .
git commit -m "Initial commit - Conflict Zero MVP"
git branch -M main
git remote add origin https://github.com/Chuos24/conflict-zero.git
git push -u origin main
```

✅ **Listo - Código en GitHub**

---

## PASO 2: Deploy Backend en Render

### 2.1 Crear Cuenta
- Ve a: https://render.com
- Regístrate con GitHub (más fácil)

### 2.2 Crear Web Service
1. Dashboard → **New Web Service**
2. Conecta tu cuenta de GitHub
3. Busca y selecciona: `conflict-zero`
4. Configuración:
   - **Name**: `conflict-zero-api`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r backend/requirements.txt`
   - **Start Command**: `cd backend && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
5. Click: **Create Web Service**

### 2.3 Configurar Variables de Entorno
En el dashboard de tu servicio, ve a **Environment** y agrega:

```
PERU_API_KEY = d02bb5a71984e759885a4e47a575715c
SECRET_KEY = cualquier-cadena-larga-y-aleatoria-aqui
ENVIRONMENT = production
```

### 2.4 Esperar Deploy
- Render compilará automáticamente
- Toma ~5 minutos la primera vez
- Cuando veas ✅ "Deploy successful", copia la URL:
  - Será algo como: `https://conflict-zero-api.onrender.com`

✅ **Listo - Backend en la nube**

---

## PASO 3: Deploy Frontend en Netlify

### 3.1 Actualizar URL del Backend

En la terminal del servidor:

```bash
cd /root/.openclaw/workspace/conflict-zero
./update-backend-url.sh https://conflict-zero-api.onrender.com
```

(Usa la URL que te dio Render)

### 3.2 Subir a Netlify

1. Ve a: https://netlify.com
2. Regístrate (puedes usar GitHub)
3. En el dashboard, arrastra el archivo:
   - `/root/.openclaw/workspace/conflict-zero/frontend/conflict-zero-static.zip`
4. Netlify deployará automáticamente
5. Te dará una URL tipo: `https://conflict-zero-abc123.netlify.app`

✅ **Listo - Frontend en la nube**

---

## 🎉 PROBANDO TODO

1. **Visita tu URL de Netlify** (el frontend)
2. **Regístrate** con cualquier email
3. **Verifica un RUC** real como `20100017491`
4. **O usa la cuenta Founder**:
   - Email: `founder@conflictzero.com`
   - Password: `FounderPass2025!`

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### El backend no conecta
- Verifica que la URL en `update-backend-url.sh` sea correcta
- Reconstruye el frontend: `cd frontend && npm run build`
- Vuelve a crear el ZIP

### Error 401 en RUCs
- La IP del servidor debe estar en allowlist de Perú API
- Ve a https://peruapi.com y agrega la IP de Render

### Build falla en Render
- Verifica que `requirements.txt` exista en `backend/`
- Asegúrate de que el comando de start sea correcto

---

## 📞 SOPORTE

Si algo falla, revisa los logs en:
- Render: Dashboard → Logs
- Netlify: Site → Deploys → Deploy Log

---

**¿Listo para empezar? Comienza con el Paso 1: GitHub** 🚀
