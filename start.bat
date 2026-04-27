@echo off
echo.
echo  InstaScope - Instagram Profile Scraper
echo  =======================================
echo.

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo  ERROR: Python no encontrado. Instala desde https://python.org
    pause
    exit /b 1
)

echo  Instalando dependencias...
pip install -r requirements.txt -q

echo  Dependencias listas.
echo.
echo  Iniciando backend en http://localhost:5000
echo  Abre frontend/index.html en tu navegador
echo.

python backend\app.py
pause
