# Copias de seguridad y restauración de la base de datos

> Procedimiento vigente para la base de datos de producción (Supabase Postgres).
> Los datos de acceso al NAS (`<IP_NAS>`, `<PUERTO_SSH>`, `<USUARIO_NAS>`,
> `<CLAVE_SSH>`, `<RUTA_PROYECTO_NAS>`) no se publican en el repositorio: están
> en la base de conocimiento privada del propietario.

## 1. Qué se copia y dónde

| Aspecto | Valor |
|---|---|
| Servicio | `db-backup` en `buenchollo-api/docker-compose.yml` (imagen `postgres:17-alpine`) |
| Script | `buenchollo-api/scripts/db_backup.sh` |
| Frecuencia | Al arrancar el contenedor y después cada 24 h (`BACKUP_INTERVAL_SECONDS`) |
| Formato | `pg_dump -Fc --no-owner --no-privileges`, validado con `pg_restore -l` (descarta copias sin datos) |
| Destino | `buenchollo-api/backups/bct-prod-<fecha>.dump` en el NAS (fuera de git) |
| Retención | 14 días (`BACKUP_RETENTION_DAYS`) |
| Conexión | `DATABASE_URL` del `.env` del NAS, pasado al pooler de **sesión** (puerto 5432): `pg_dump` no funciona con el de transacciones (6543) |

**RPO** (pérdida máxima de datos): 24 h. **RTO** (tiempo de recuperación): ~15 min
para una restauración completa.

**Pendiente del propietario**: una copia **fuera del NAS** (si el NAS se pierde, las
copias también). Opciones: Synology Hyper Backup de la carpeta `backups/` a un
destino externo, o un plan de Supabase con backups gestionados / PITR.

## 2. Comprobar que funciona

```bash
ssh -p <PUERTO_SSH> -i <CLAVE_SSH> <USUARIO_NAS>@<IP_NAS>
DOCKER="sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker"
$DOCKER logs --tail 5 buenchollo-db-backup     # «[db-backup] OK … (N tablas con datos …)»
ls -lh <RUTA_PROYECTO_NAS>/buenchollo-api/backups/
```

Si el log muestra `ERROR`, el contenedor sigue vivo y reintenta en el siguiente ciclo;
revisa el `DATABASE_URL` del `.env` y la conectividad con Supabase.

**Copia manual inmediata** (p. ej. antes de una migración): `$DOCKER restart buenchollo-db-backup`.

## 3. Restaurar

> Restaurar sobre producción **sobrescribe datos**. Hazlo primero en local y, en
> producción, solo tras parar la API y el scheduler.

### 3.1 Probar la copia en local (recomendado cada mes)

Con el entorno local (`.\local-env\bct-local.cmd start`, ver
[`LOCAL-ENV.md`](LOCAL-ENV.md)), que incluye Postgres 17:

```bash
pg_restore --list bct-prod-<fecha>.dump | head          # índice legible
createdb -h localhost -p <PUERTO_PG_LOCAL> -U postgres bct_restore_test
pg_restore -h localhost -p <PUERTO_PG_LOCAL> -U postgres -d bct_restore_test \
  --no-owner --no-privileges bct-prod-<fecha>.dump
```

Los errores sobre esquemas o roles propios de Supabase (`auth`, `storage`,
`supabase_admin`…) son esperables en un Postgres sin Supabase; lo importante es que
las tablas de `public` tengan datos.

### 3.2 Restaurar en producción

1. Parar la escritura: `$DOCKER stop buenchollo-api buenchollo-scheduler`.
2. Restaurar las tablas afectadas (o todo el esquema `public`) contra el pooler de
   sesión de Supabase:
   ```bash
   pg_restore --clean --if-exists --no-owner --no-privileges --schema=public \
     -d "postgresql://<USUARIO_DB>:<PASSWORD_DB>@<HOST_POOLER>:5432/postgres" \
     bct-prod-<fecha>.dump
   ```
3. Comprobar la revisión de Alembic (`alembic current` dentro del contenedor de la API)
   y que coincide con el código desplegado.
4. Arrancar: `$DOCKER start buenchollo-api buenchollo-scheduler` y verificar
   `https://api.buenchollotech.com/health/ready`.

## 4. Antes de cada migración

Toda migración de Alembic se despliega con una copia reciente: reiniciar
`buenchollo-db-backup`, esperar al `OK` en su log y anotar el fichero en
`PROJECT_STATUS.md`.
