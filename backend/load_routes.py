# Este archivo carga las rutas de registro
# Se ejecuta al inicio de la aplicación
import sys
import os

# Agregar el directorio backend al path
backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Intentar importar y registrar las rutas
try:
    from registration_routes import router as registration_router
    print("✅ Registration routes importadas correctamente")
except Exception as e:
    print(f"⚠️ Error importando registration routes: {e}")
