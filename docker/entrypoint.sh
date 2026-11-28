#!/bin/sh
set -e

echo "Verificando e inicializando base de datos..."
python /app/inicializar_bd.py

echo "Iniciando servidor Flask en 0.0.0.0:${PORT:-5000}..."
if [ "${FLASK_DEBUG:-0}" = "1" ]; then
    exec flask --app app run --host=0.0.0.0 --port="${PORT:-5000}" --debug
else
    exec flask --app app run --host=0.0.0.0 --port="${PORT:-5000}"
fi
