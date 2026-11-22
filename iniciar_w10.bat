@echo off
chcp 65001 >nul
title Control de Estudio - E. B. N. Los Laureles
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
    echo [AVISO] El sistema aun no ha sido instalado.
    echo         Ejecute primero instalar_w10.bat para preparar el entorno.
    echo.
    pause
    exit /b 1
)

call venv\Scripts\activate.bat

:: Verificar si MySQL (XAMPP) esta activo en el puerto 3306; si no, intentar arrancarlo
python -c "import socket,sys; s=socket.socket(); s.settimeout(1.5); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
if errorlevel 1 (
    if exist "C:\xampp\mysql\bin\mysqld.exe" (
        echo Iniciando MySQL de XAMPP automaticamente...
        start "" /min "C:\xampp\mysql\bin\mysqld.exe" --defaults-file="C:\xampp\mysql\bin\my.ini" --standalone
        timeout /t 4 /nobreak >nul
    ) else (
        echo [AVISO] MySQL no esta iniciado en el puerto 3306.
        echo         Inicie el modulo MySQL desde el Panel de Control de XAMPP y reintente.
        echo.
        pause
        exit /b 1
    )
)

echo ========================================================================
echo   Control de Estudio - E. B. N. "Los Laureles"
echo   Servidor local activo en: http://127.0.0.1:5000
echo   No cierre esta ventana mientras el sistema este en uso.
echo ========================================================================
echo.

:: Abrir el navegador 2 segundos despues para asegurar que Flask ya este escuchando
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5000"
python app.py
pause
