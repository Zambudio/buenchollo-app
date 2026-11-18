#!/bin/sh
# Copia de seguridad diaria de la base de datos de producción (AUD-03).
#
# La ejecuta el servicio `db-backup` de docker-compose.yml (imagen postgres:17).
# Usa el DATABASE_URL del .env del NAS, pasado al pooler de sesión (puerto
# 5432): pg_dump no funciona con el pooler de transacciones (6543).
#
# - Formato custom (-Fc), validado con `pg_restore -l` antes de darlo por bueno.
# - Retención: BACKUP_RETENTION_DAYS días (14 por defecto).
# - Se ejecuta al arrancar el contenedor y después cada BACKUP_INTERVAL_SECONDS.
# - Nunca imprime la URL ni la contraseña.
set -u

BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
INTERVAL_SECONDS="${BACKUP_INTERVAL_SECONDS:-86400}"

session_url() {
  echo "$DATABASE_URL" | sed -e 's#^postgresql+asyncpg://#postgresql://#' -e 's#:6543/#:5432/#'
}

backup_once() {
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  file="$BACKUP_DIR/bct-prod-$ts.dump"
  if ! pg_dump -Fc --no-owner --no-privileges -f "$file.tmp" "$(session_url)"; then
    echo "[db-backup] ERROR: pg_dump falló ($ts)"
    rm -f "$file.tmp"
    return 1
  fi
  tables=$(pg_restore -l "$file.tmp" 2>/dev/null | grep -c "TABLE DATA")
  if [ "$tables" -eq 0 ]; then
    echo "[db-backup] ERROR: copia sin datos de tablas ($ts); se descarta"
    rm -f "$file.tmp"
    return 1
  fi
  mv "$file.tmp" "$file"
  sha=$(sha256sum "$file" | cut -c1-16)
  size=$(du -h "$file" | cut -f1)
  echo "[db-backup] OK $file ($size, $tables tablas con datos, sha256 $sha…)"
  find "$BACKUP_DIR" -name 'bct-prod-*.dump' -mtime +"$RETENTION_DAYS" -delete
}

if [ -z "${DATABASE_URL:-}" ]; then
  echo "[db-backup] ERROR: falta DATABASE_URL"
  exit 1
fi
mkdir -p "$BACKUP_DIR"
while true; do
  backup_once
  sleep "$INTERVAL_SECONDS"
done
