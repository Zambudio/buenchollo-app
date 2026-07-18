#!/usr/bin/env bash
# Levanta la API en local (uvicorn) para probar el frontend en desarrollo
# contra datos reales, sin depender de CORS abierto a buenchollotech.com
# ni de tocar el .env real.
#
# Importante: usa la MISMA base de datos que producción (no hay una BD
# de pruebas separada). Leer/navegar es seguro; votar, dar a favorito o
# comentar SÍ escribe datos reales. Úsalo con esa cabeza.
#
# El scheduler queda desactivado para que no dispare tareas en segundo
# plano (publicar en Telegram, marcar caducados, etc.) durante la prueba.
#
# Uso: desde buenchollo-api/  ->  ./scripts/dev_local.sh

set -euo pipefail
cd "$(dirname "$0")/.."

export CORS_ORIGINS='["http://localhost:8080"]'
export SCHEDULER_ENABLED=false
export APP_ENV=local

echo "→ API local en http://localhost:8000 (CORS limitado a http://localhost:8080, scheduler OFF)"
echo "→ Usa la base de datos de PRODUCCIÓN. Votos/favoritos/comentarios que hagas aquí son reales."

PYTHON=./.venv/Scripts/python.exe
[ -x "$PYTHON" ] || PYTHON=./.venv/bin/python

exec "$PYTHON" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
