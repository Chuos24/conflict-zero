#!/bin/bash
# Script de build para Render con Python 3.11 forzado

echo "Forzando Python 3.11..."
export PYTHON_VERSION=3.11.0

cd backend
pip install --upgrade pip
pip install -r requirements.txt
