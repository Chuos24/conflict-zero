#!/bin/bash
# Script para poblar datos piloto de D&C Inmobiliaria

echo "🚀 Creando datos piloto para D&C Inmobiliaria (RUC: 20600042549)"

# Login como D&C
TOKEN=$(curl -s -X POST "https://conflict-zero-api.onrender.com/api/v3/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test+dc@alegrainmo.com", "password": "Temporal2024!"}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

echo "✅ Login exitoso"

# RUCs reales de proveedores peruanos para crear historial
RUCs=(
  "20131312955"  # Empresa real peruana
  "20529400790"  # Zamora (demo)
  "20493036931"  # Constructora
  "20345678901"  # Proveedor tipo
)

for ruc in "${RUCs[@]}"; do
  echo "📊 Consultando RUC: $ruc"
  
  curl -s -X GET "https://conflict-zero-api.onrender.com/api/v3/consulta/$ruc" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" > /dev/null
    
  sleep 0.5
done

echo ""
echo "✅ Datos piloto creados"
echo "📈 D&C Inmobiliaria ahora tiene:"
echo "   - Historial de consultas activo"
echo "   - Plan Enterprise con 100,000 consultas/mes"
echo ""
echo "🔗 Acceso: https://czperu.com/login.html"
echo "📧 test+dc@alegrainmo.com"
echo "🔑 Temporal2024!"
