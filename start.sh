#!/bin/bash
# ── InstaScope — Script de inicio rápido ──

echo ""
echo "  ██╗███╗   ██╗███████╗████████╗ █████╗ ███████╗ ██████╗ ██████╗ ██████╗ ███████╗"
echo "  ██║████╗  ██║██╔════╝╚══██╔══╝██╔══██╗██╔════╝██╔════╝██╔═══██╗██╔══██╗██╔════╝"
echo "  ██║██╔██╗ ██║███████╗   ██║   ███████║███████╗██║     ██║   ██║██████╔╝█████╗  "
echo "  ██║██║╚██╗██║╚════██║   ██║   ██╔══██║╚════██║██║     ██║   ██║██╔═══╝ ██╔══╝  "
echo "  ██║██║ ╚████║███████║   ██║   ██║  ██║███████║╚██████╗╚██████╔╝██║     ███████╗"
echo "  ╚═╝╚═╝  ╚═══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚══════╝ ╚═════╝ ╚═════╝ ╚═╝     ╚══════╝"
echo ""
echo "  Instagram Profile Scraper — Uso Educativo"
echo "  ─────────────────────────────────────────"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "  ❌ Python 3 no encontrado. Instálalo desde https://python.org"
    exit 1
fi

echo "  ✓ Python $(python3 --version | cut -d' ' -f2) detectado"

# Install deps
echo "  → Instalando dependencias..."
pip install -r requirements.txt -q

echo "  ✓ Dependencias instaladas"
echo ""
echo "  🚀 Iniciando backend en http://localhost:5000"
echo "  📂 Abre frontend/index.html en tu navegador"
echo ""

# Start backend
python3 backend/app.py
