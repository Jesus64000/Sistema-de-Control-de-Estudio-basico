@echo off
chcp 65001 >nul
title Instalacion Completa - Control de Estudio E. B. N. Los Laureles
cd /d "%~dp0"

echo ========================================================================
echo   INSTALACION INICIAL - CONTROL DE ESTUDIO E. B. N. "LOS LAURELES"
echo   Entorno: Windows 10 + XAMPP (MySQL/MariaDB) + Python 3
echo ========================================================================
echo.

:: 1. Verificar Python (comprobando ejecucion real para evitar falso positivo del alias de Microsoft Store)
python --version >nul 2>&1
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
if exist venv (
    if not exist venv\Scripts\python.exe (
        echo       Se detecto un entorno virtual incompatible con Windows.
        echo       Recreando entorno virtual compatible con Windows...
        rmdir /s /q venv
    )
)
if not exist venv\Scripts\python.exe (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual venv.
        pause
        exit /b 1
    )
)
call venv\Scripts\activate.bat
venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1
venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Fallo la instalacion de librerias. Verifique su conexion a internet.
    pause
    exit /b 1
)

:: 3. Crear archivo .env si no existe (desde .env.example o con valores estandar XAMPP)
if not exist .env (
    if exist .env.example (
        copy .env.example .env >nul
        echo       Archivo .env creado desde .env.example.
    ) else (
        (
            echo DB_HOST=127.0.0.1
            echo DB_PORT=3306
            echo DB_USER=root
            echo DB_PASSWORD=
            echo DB_NAME=los_laureles_ce
            echo FLASK_DEBUG=0
            echo PORT=5000
        ) > .env
        echo       Archivo .env generado con configuracion estandar de XAMPP.
    )
)

:: Detectar ruta de XAMPP (C:, D: o E:)
set "XAMPP_DIR="
for %%D in (C D E) do (
    if not defined XAMPP_DIR (
        if exist "%%D:\xampp\mysql\bin\mysqld.exe" set "XAMPP_DIR=%%D:\xampp"
    )
)

:: 4. Verificar o iniciar MySQL de XAMPP en puerto 3306
echo.
echo [2/4] Verificando servicio MySQL / MariaDB de XAMPP (puerto 3306)...
venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(1.5); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
if errorlevel 1 (
    if defined XAMPP_DIR (
        echo       MySQL no estaba iniciado. Arrancandolo desde %XAMPP_DIR%...
        start "" /min "%XAMPP_DIR%\mysql\bin\mysqld.exe" --defaults-file="%XAMPP_DIR%\mysql\bin\my.ini" --standalone
        venv\Scripts\python.exe -c "import socket,time; [time.sleep(1) for _ in range(10) if socket.socket().connect_ex(('127.0.0.1',3306))!=0]"
    )
)

venv\Scripts\python.exe -c "import socket,sys; s=socket.socket(); s.settimeout(2); rc=s.connect_ex(('127.0.0.1',3306)); s.close(); sys.exit(0 if rc==0 else 1)"
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
if defined XAMPP_DIR (
    if exist "%XAMPP_DIR%\mysql\bin\mysql.exe" (
        if exist "database\instalacion_completa_xampp.sql" (
            echo       Importando database\instalacion_completa_xampp.sql en XAMPP...
            "%XAMPP_DIR%\mysql\bin\mysql.exe" -u root --default-character-set=utf8mb4 < "database\instalacion_completa_xampp.sql"
            if errorlevel 1 (
                echo       [AVISO] No se pudo importar con root sin clave; se intentara con inicializar_bd.py y .env...
            )
        )
    )
)

echo       Verificando migraciones e integridad con inicializar_bd.py...
venv\Scripts\python.exe inicializar_bd.py
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
choice /c SN /n /m "Desea iniciar el sistema ahora? [S/N]: "
if errorlevel 2 goto :fin
if errorlevel 1 call "%~dp0iniciar_w10.bat"

:fin
