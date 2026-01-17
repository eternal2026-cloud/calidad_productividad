@echo off
REM Script para inicializar y subir el proyecto a GitHub
REM Autor: El Pedregal S.A. - Departamento de BI

echo ==========================================
echo   Deployment a GitHub - El Pedregal S.A.
echo ==========================================
echo.

REM Verificar que estamos en la carpeta correcta
if not exist "pru.py" (
    echo ERROR: No se encuentra pru.py en esta carpeta
    echo Asegurate de ejecutar este script desde la carpeta del proyecto
    pause
    exit /b 1
)

echo [1/6] Inicializando repositorio Git...
git init

echo.
echo [2/6] Agregando archivos al staging...
git add .

echo.
echo [3/6] Verificando archivos a subir...
echo.
echo === IMPORTANTE: Verifica que secrets.toml NO aparezca en la lista ===
echo.
git status
echo.
pause

echo.
echo [4/6] Creando primer commit...
git commit -m "Initial commit: BI Productividad El Pedregal con integracion Google Sheets"

echo.
echo [5/6] Conectando con repositorio remoto...
git remote add origin https://github.com/eternal2026-cloud/productividad_calidad.git

echo.
echo [6/6] Subiendo archivos a GitHub...
git branch -M main
git push -u origin main

echo.
echo ==========================================
echo   Deployment completado!
echo ==========================================
echo.
echo Verifica tu repositorio en:
echo https://github.com/eternal2026-cloud/productividad_calidad
echo.
pause
