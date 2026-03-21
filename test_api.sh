#!/bin/bash
# Script de prueba para verificar datos reales con Perú API y Decolecta

echo "🧪 Probando Conflict Zero con datos reales..."
echo "=============================================="
echo "Perú API: d02bb5a71984e759885a4e47a575715c"
echo "Decolecta: sk_13991.goSIIB6mxd6VjO9gzZGxytwnOYa9z0uU"
echo ""

API_URL=${1:-"https://xvyrpa0bhf.execute-api.us-east-1.amazonaws.com/prod"}

echo "📡 URL de API: $API_URL"
echo ""

# Test 1: RUC de Interbank (20100017491)
echo "Test 1: Consultando RUC 20100017491 (Interbank)..."
RESPONSE=$(curl -s "$API_URL/consulta-osce/20100017491")
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

# Verificar si es dato real
if echo "$RESPONSE" | grep -q '"datos_reales": true'; then
    echo "✅ Datos reales confirmados"
    if echo "$RESPONSE" | grep -q '"sunat": "peruapi_sunat"'; then
        echo "✅ Fuente: Perú API"
    elif echo "$RESPONSE" | grep -q '"sunat": "decolecta_sunat"'; then
        echo "✅ Fuente: Decolecta"
    fi
else
    echo "❌ ERROR: No se obtuvieron datos reales"
fi
echo ""

# Test 2: RUC de BCP (20100043140)
echo "Test 2: Consultando RUC 20100043140 (BCP)..."
curl -s "$API_URL/consulta-osce/20100043140" | python3 -m json.tool 2>/dev/null || echo "Error en parseo JSON"
echo ""

# Test 3: RUC inválido (debe dar error)
echo "Test 3: RUC inválido (123)..."
curl -s "$API_URL/consulta-osce/123" | python3 -m json.tool 2>/dev/null || echo "Error en parseo JSON"
echo ""

echo "=============================================="
echo "✅ Pruebas completadas"
echo ""
echo "Verifica que:"
echo "1. Los datos de 'razon_social' sean reales (ej: INTERBANK S.A.)"
echo "2. 'datos_reales' sea true"
echo "3. 'fuentes_datos.sunat' diga 'peruapi_sunat' o 'decolecta_sunat'"
echo "4. La dirección sea real (no ficticia)"
echo "5. El score se calcule correctamente (0-100)"
