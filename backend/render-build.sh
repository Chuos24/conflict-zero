#!/bin/bash
# render-build.sh - Build script for Render with Redis support

echo "=== Conflict Zero API Build ==="
echo "Python version: $(python --version)"

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "=== Build complete ==="
