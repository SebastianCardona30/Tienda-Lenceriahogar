@echo off
chcp 65001 >nul 2>nul
title Publicar la tienda en Vercel
cd /d "%~dp0"

echo ==================================================
echo   PUBLICAR EN VERCEL (plan gratis)
echo ==================================================
echo.
echo Requisitos:
echo   1. Node.js instalado: https://nodejs.org  (gratuito)
echo   2. Cuenta gratuita en Vercel: https://vercel.com/signup
echo   3. Haber iniciado sesion una vez:  npx vercel login
echo.

where npx >nul 2>nul
if errorlevel 1 (
    echo NO SE ENCONTRO NODE.JS. Falta el comando npx.
    echo Instalalo desde https://nodejs.org y vuelve a ejecutar este archivo.
    echo.
    pause
    exit /b 1
)

echo Publicando la version de produccion...
echo (la primera vez preguntara: responde con tu cuenta de Vercel)
echo.
npx --yes vercel@latest deploy --prod

echo.
echo ==================================================
echo  Listo. La direccion de tu tienda aparece arriba
echo  (algo como https://tu-proyecto.vercel.app)
echo ==================================================
pause
