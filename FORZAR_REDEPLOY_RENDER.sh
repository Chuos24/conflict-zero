#!/bin/bash
# Forzar redeploy del servicio en Render

echo "═══════════════════════════════════════════════════════════"
echo "🔄 FORZAR REDEPLOY - Conflict Zero Backend"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Opción 1: Usar Render CLI si está disponible
if command -v render &> /dev/null; then
    echo "✅ Render CLI encontrado"
    echo "🚀 Forzando redeploy..."
    render deploy --service conflictzero-backend1 --confirm
else
    echo "⚠️ Render CLI no disponible"
    echo ""
    echo "📋 INSTRUCCIONES MANUALES:"
    echo ""
    echo "1. Ve a: https://dashboard.render.com/web/services"
    echo ""
    echo "2. Busca tu servicio: conflictzero-backend1"
    echo ""
    echo "3. Haz click en 'Manual Deploy' → 'Deploy latest commit'"
    echo ""
    echo "   O alternativamente:"
    echo "   - Ve a la pestaña 'Settings'"
    echo "   - Cambia cualquier variable de entorno (y luego vuelve a ponerla)"
    echo "   - Esto forzará un redeploy"
    echo ""
    echo "4. Espera ~2 minutos a que termine"
    echo ""
    echo "5. Verifica con:"
    echo "   curl https://conflictzero-backend1.onrender.com/debug/tce-raw"
    echo ""
fi

echo "═══════════════════════════════════════════════════════════"