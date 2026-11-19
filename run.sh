#!/usr/bin/env bash
set -euo pipefail

# -----------------------------------------------------------------------------
# METADATA / HELP
# -----------------------------------------------------------------------------
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
PROGRAM=$(basename "$0")
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.cache/uv}"
PYTHON="${BOOKORBIT_PYTHON:-3.15}"
HELP=$(cat <<HELP
BookOrbit Control — Panel local para la biblioteca BookOrbit y sus servicios Docker.
Usage: ./$PROGRAM COMMAND [service...]

  gui             Abrir panel (predeterminado: Tkinter; --ui webview para HTML)
  build           Preparar el entorno con uv y crear dist/BookOrbit Control.app
  install         Copiar la app construida a ~/Applications
  start [service] Iniciar servicios con Docker Compose
  stop [service]  Detener sin borrar contenedores ni datos
  restart [...]   Reiniciar servicios existentes
  status          Mostrar estado de todos los servicios y perfiles
  logs [service]  Seguir docker compose logs (Ctrl-C para terminar)
  lint            Revisar código y formato con Ruff (sin modificar)
  format          Aplicar formato Ruff
  browse          Abrir BookOrbit en el navegador
  --help          Mostrar ayuda

Docker Desktop debe estar iniciado. Los datos y secretos viven fuera de la .app.
HELP
)

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------
_compose() {
    local config="${BOOKORBIT_RUNTIME_DIR:-$HOME/Library/Application Support/BookOrbit Control/runtime}"
    docker compose --project-directory "$config" --env-file "$config/.env" -f "$config/compose.yaml" "$@"
}
start() { _compose up -d "$@"; }
stop() { _compose stop "$@"; }
restart() { _compose restart "$@"; }
status() { _compose --profile '*' ps -a "$@"; }
logs() { _compose logs --tail=100 --follow "$@"; }
browse() { uv run --python "$PYTHON" python app.py --browse; }
gui() { uv run --python "$PYTHON" python app.py "$@"; }
lint() {
    uv run --python "$PYTHON" ruff check .
    uv run --python "$PYTHON" ruff format --check .
}
format() { uv run --python "$PYTHON" ruff format .; }
build() {
    uv sync --python "$PYTHON" --group build
    uv run --no-sync python -c 'import tkinter; print("Tk", tkinter.TkVersion)'
    uv run --no-sync python scripts/build.py
    printf '\nApp creada: %s/dist/BookOrbit Control.app\n' "$ROOT"
}
install() {
    [[ -d "dist/BookOrbit Control.app" ]] || { printf 'Ejecuta ./run.sh build primero.\n' >&2; exit 1; }
    mkdir -p "$HOME/Applications"
    ditto "dist/BookOrbit Control.app" "$HOME/Applications/BookOrbit Control.app"
}

# -----------------------------------------------------------------------------
# ENTRYPOINT
# -----------------------------------------------------------------------------
command="${1:---help}"
case "$command" in
    --help|help) printf '%s\n' "$HELP" ;;
    start|stop|restart|status|logs|browse|gui|build|install|lint|format) "$command" "${@:2}" ;;
    *) printf 'Unknown command: %s\n' "$command" >&2; exit 1 ;;
esac
