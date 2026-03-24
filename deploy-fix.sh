#!/bin/bash
# deploy-fix.sh - Script para desplegar los arreglos

echo "=== DEPLOY DE ARREGLOS CONFLICT ZERO ==="
echo ""

# Verificar AWS CLI
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI no encontrado. Instálalo primero:"
    echo "   https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html"
    exit 1
fi

# 1. Actualizar Lambda
echo "1. Actualizando Lambda function..."
cd /root/.openclaw/workspace/conflict-zero/aws/lambda

# Desplegar versión v9 (con soporte Perú API)
aws lambda update-function-code \
    --function-name conflict-zero-api \
    --zip-file fileb://lambda_uhnw_v9.zip \
    --region us-east-1

if [ $? -eq 0 ]; then
    echo "✅ Lambda actualizada exitosamente (v9 - con Perú API fallback)"
else
    echo "⚠️  Error actualizando Lambda. Verifica:"
    echo "   - Tienes AWS CLI configurado (aws configure)"
    echo "   - El nombre de la función es 'conflict-zero-api' o cámbialo en este script"
    echo "   - Tienes permisos en AWS"
fi

# 2. Subir HTML a S3
echo ""
echo "2. Subiendo dashboard.html a S3..."

cd /root/.openclaw/workspace/conflict-zero-static

aws s3 cp dashboard.html s3://conflictzero-certificados-prod/dashboard.html \
    --acl public-read \
    --content-type text/html

if [ $? -eq 0 ]; then
    echo "✅ Dashboard subido exitosamente"
else
    echo "⚠️  Error subiendo a S3. Verifica el nombre del bucket."
fi

echo ""
echo "=== DEPLOY COMPLETADO ==="
echo "Prueba en: https://czperu.com/dashboard.html"
echo ""
echo "Cambios aplicados:"
echo "  - Lambda ahora consulta Decolecta PRIMERO, y si falla usa Perú API"
echo "  - Si ambas APIs fallan, muestra '⚠️ RUC NO ENCONTRADO EN SUNAT'"
echo "  - Frontend maneja mejor los errores con timeout de 15s"
