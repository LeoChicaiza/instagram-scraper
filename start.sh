#!/bin/bash
echo ""
echo "  InstaScope — Instagram Scraper"
echo "  ================================"
echo ""

if ! command -v python3 &>/dev/null; then
  echo "  ✗ Python 3 no encontrado."
  exit 1
fi

echo "  → Instalando dependencias..."
pip install -r requirements.txt -q

echo "  ✓ Listo"
echo "  → Backend en http://localhost:5000"
echo "  → Abre frontend/index.html en tu navegador"
echo ""
python3 backend/app.py
