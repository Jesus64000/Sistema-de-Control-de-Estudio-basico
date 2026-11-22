@echo off
chcp 65001 >nul
title Instalacion Completa - Control de Estudio E. B. N. Los Laureles
cd /d "%~dp0"

echo ========================================================================
echo   INSTALACION INICIAL - CONTROL DE ESTUDIO E. B. N. "LOS LAURELES"
echo   Entorno: Windows 10 + XAMPP (MySQL/MariaDB) + Python 3
echo ========================================================================
echo.

:: 1. Verificar Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] No se encontro Python en el sistema.
    echo         Instale Python 3.10 o superior desde https://www.python.org/
    echo         y marque la casilla "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

:: 2. Crear entorno virtual e instalar dependencias
echo [1/4] Preparando entorno virtual Python y dependencias...
if not exist venv (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual venv.
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de librerias. Verifique su conexion a internet.
    pause
    exit /b 1
)

:: 3. Crear archivo .env si no existe
if not exist .env (
    copy .env.example .env >nul
    echo       Archivo .env creado desde .env.example.
)

:: 4. Verificar o iniciar MySQL de XAMPP en puerto 3306
echo.
echo [2/4] Verificando servicio MySQL / MariaDB de XAMPP (puerto 3306)...
python -c "import socket,sys; s=socket.socket(); s.settimeout(1.5); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
if errorlevel 1 (
    if exist "C:\xampp\mysql\bin\mysqld.exe" (
        echo       MySQL no estaba iniciado. Intentando arrancarlo desde C:\xampp...
        start "" /min "C:\xampp\mysql\bin\mysqld.exe" --defaults-file="C:\xampp\mysql\bin\my.ini" --standalone
        timeout /t 4 /nobreak >nul
    )
)

python -c "import socket,sys; s=socket.socket(); s.settimeout(2); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
if errorlevel 1 (
    echo.
    echo [AVISO] No se detecto MySQL activo en el puerto 3306.
    echo         Abra el Panel de Control de XAMPP, pulse "Start" en MySQL
    echo         y luego presione una tecla para continuar...
    pause
)

:: 5. Importar script SQL completo (si existe mysql.exe de XAMPP) y ejecutar inicializador Python
echo.
echo [3/4] Creando base de datos, tablas y datos base en MySQL (XAMPP)...
if exist "C:\xampp\mysql\bin\mysql.exe" (
    if exist "database\instalacion_completa_xampp.sql" (
        echo       Importando database\instalacion_completa_xampp.sql en XAMPP...
        "C:\xampp\mysql\bin\mysql.exe" -u root --default-character-set=utf8mb4 < "database\instalacion_completa_xampp.sql"
    )
)

echo       Verificando migraciones e integridad con inicializar_bd.py...
python inicializar_bd.py
if errorlevel 1 (
    echo.
    echo [ERROR] No se pudo inicializar la base de datos.
    echo         Verifique que MySQL este iniciado en XAMPP y revise el archivo .env.
    pause
    exit /b 1
)

echo.
echo [4/4] Instalacion completada con exito.
echo ========================================================================
echo   Credenciales iniciales (el sistema pedira cambiarlas al entrar):
echo     Administrador : admin    / admin123
echo     Operador      : operador / operador123
echo.
echo   Para abrir el sistema haga doble clic en: iniciar_w10.bat
echo ========================================================================
echo.
pause
