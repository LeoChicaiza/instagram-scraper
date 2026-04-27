@echo off
echo.
echo  InstaScope - Instagram Scraper
echo  ================================
echo.
pip install -r requirements.txt -q
echo  Backend iniciando en http://localhost:5000
echo  Abre frontend\index.html en tu navegador
echo.
python backend\app.py
pause
