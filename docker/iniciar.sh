#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
URL="http://127.0.0.1:5000"

if ! command -v docker >/dev/null 2>&1; then
    echo "Error: Docker no está instalado."
    exit 1
fi

DOCKER_CMD=(docker)

asegurar_docker() {
    if docker info >/dev/null 2>&1; then
        DOCKER_CMD=(docker)
        return 0
    fi

    echo "Iniciando servicio de Docker (puede pedir tu contraseña de sudo)..."
    sudo systemctl start docker

    if docker info >/dev/null 2>&1; then
        DOCKER_CMD=(docker)
    elif sudo docker info >/dev/null 2>&1; then
        DOCKER_CMD=(sudo docker)
    else
        echo "Error: No se pudo conectar con el servicio de Docker."
        exit 1
    fi
}

esperar_sistema() {
    echo "Esperando a que el sistema esté listo en $URL..."
    for _ in $(seq 1 60); do
        if command -v curl >/dev/null 2>&1; then
            if curl -fsS -o /dev/null "$URL"; then
                return 0
            fi
        elif python3 -c "import urllib.request; urllib.request.urlopen('$URL', timeout=2)" >/dev/null 2>&1; then
            return 0
        fi
        sleep 2
    done
    echo "Advertencia: El sistema tardó más de lo esperado en responder. Revisa con: $0 logs"
    return 1
}

abrir_navegador() {
    if [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] && command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 &
    fi
}

asegurar_docker

ACCION="${1:-up}"

case "$ACCION" in
    up|start)
        echo "Construyendo e iniciando contenedores (MariaDB + Flask)..."
        "${DOCKER_CMD[@]}" compose -f "$COMPOSE_FILE" up --build -d

        if esperar_sistema; then
            echo ""
            echo "Sistema listo para ingresar:"
            echo "  URL: $URL"
            echo "  Admin inicial:    admin / admin123"
            echo "  Operador inicial: operador / operador123"
            abrir_navegador
        fi
        echo ""
        echo "Comandos útiles:"
        echo "  $0 logs    -> Ver logs en tiempo real"
        echo "  $0 down    -> Detener contenedores"
        echo "  $0 reset   -> Detener y borrar volumen de BD (reinicio limpio)"
        ;;
    down|stop)
        "${DOCKER_CMD[@]}" compose -f "$COMPOSE_FILE" down
        ;;
    logs)
        "${DOCKER_CMD[@]}" compose -f "$COMPOSE_FILE" logs -f
        ;;
    reset)
        echo "Deteniendo contenedores y eliminando volumen de base de datos..."
        "${DOCKER_CMD[@]}" compose -f "$COMPOSE_FILE" down -v
        ;;
    status|ps)
        "${DOCKER_CMD[@]}" compose -f "$COMPOSE_FILE" ps
        ;;
    *)
        echo "Uso: $0 [up|down|logs|reset|status]"
        exit 1
        ;;
esac
