@echo off
chcp 65001 >nul 2>nul
title Lenceria de Hogar Ciudad Bonita - Tienda
cd /d "%~dp0"

echo ==================================================
echo   LENCERIA DE HOGAR CIUDAD BONITA - Tienda
echo   Inicio rapido (Windows)
echo ==================================================
echo.

REM [1/4] Entorno virtual de Python
if not exist venv (
    echo [1/4] Creando el entorno virtual la primera vez...
    python -m venv venv 2>nul || py -3 -m venv venv
    if not exist venv (
        echo.
        echo NO SE ENCONTRO PYTHON. Instalalo desde https://www.python.org/downloads/
        echo (marca la casilla "Add Python to PATH" al instalar).
        pause
        exit /b 1
    )
) else (
    echo [1/4] Entorno virtual listo.
)

REM [2/4] Dependencias (gratuitas; ver README.md)
echo [2/4] Instalando dependencias (solo la primera vez tarda)...
venv\Scripts\python -m pip install -q -r requirements.txt

REM [3/4] Base de datos con datos demo
echo [3/4] Preparando la base de datos...
venv\Scripts\python manage.py migrate --noinput
venv\Scripts\python manage.py seed_demo

REM [4/4] Abrir la tienda y arrancar el servidor
echo [4/4] Abriendo la tienda en el navegador...
start "" http://127.0.0.1:8000/
echo.
echo  La tienda queda corriendo en  http://127.0.0.1:8000/
echo  Panel de administracion:        http://127.0.0.1:8000/admin/
echo  Para detener el servidor:       Ctrl + C en esta ventana
echo.
venv\Scripts\python manage.py runserver

pause
