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

if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
    )
)

call venv\Scripts\activate.bat

:: Detectar ruta de XAMPP (C:, D: o E:)
set "XAMPP_DIR="
for %%D in (C D E) do (
    if not defined XAMPP_DIR (
        if exist "%%D:\xampp\mysql\bin\mysqld.exe" set "XAMPP_DIR=%%D:\xampp"
    )
)

:: Verificar si MySQL (XAMPP) esta activo en el puerto 3306; si no, intentar arrancarlo
venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1.5); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
if errorlevel 1 (
    if defined XAMPP_DIR (
        echo Iniciando MySQL de XAMPP automaticamente desde %XAMPP_DIR%...
        start "" /min "%XAMPP_DIR%\mysql\bin\mysqld.exe" --defaults-file="%XAMPP_DIR%\mysql\bin\my.ini" --standalone
        venv\Scripts\python.exe -c "import socket,time; [time.sleep(1) for _ in range(10) if socket.socket().connect_ex(('127.0.0.1',3306))!=0]"
    )
)

venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(2); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
if errorlevel 1 (
    echo [AVISO] MySQL no esta iniciado en el puerto 3306.
    echo         Inicie el modulo MySQL desde el Panel de Control de XAMPP y reintente.
    echo.
    pause
    exit /b 1
)

echo ========================================================================
echo   Control de Estudio - E. B. N. "Los Laureles"
echo   Servidor local activo en: http://127.0.0.1:5000
echo   No cierre esta ventana mientras el sistema este en uso.
echo ========================================================================
echo.

:: Abrir el navegador 2 segundos despues para asegurar que Flask ya este escuchando
start "" /b cmd /c "ping -n 3 127.0.0.1 >nul && start http://127.0.0.1:5000"
venv\Scripts\python.exe app.py
pause
