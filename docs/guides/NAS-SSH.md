# 🔐 NAS-SSH — Conexión SSH al NAS (guía para IAs)

> Los valores reales (IP, puerto, usuario, clave y rutas) no se publican en el repositorio: están en la base de conocimiento privada del propietario (OBSIDIAN VAULT, ficha `Entities/Infraestructura-NAS-Synology-DS224.md`).

Para qué sirve: que un agente de IA pueda conectarse por SSH al NAS Synology, inspeccionar contenedores y reiniciar o reconstruir `buenchollo-api` sin intervención manual. En esta guía `<IP_NAS>`, `<PUERTO_SSH>`, `<USUARIO_NAS>`, `<CLAVE_SSH>`, `<ALIAS_NAS>` y `<RUTA_SHARE>` son marcadores.

Última revisión: 2026-11-18.

---

## 0. Resumen para quien tenga prisa

- Conectar: `ssh <ALIAS_NAS>` (alias configurado en la máquina de trabajo, ver §2).
- **Docker no está en el `PATH`**: usar `sudo -n` con la ruta completa (`/volume1/@appstore/ContainerManager/usr/bin/docker`).
- Usar `docker-compose` (con guion), **no** `docker compose`: este NAS solo tiene el binario clásico.
- **No hay `git` en el NAS**. El código de `buenchollo-api` llega porque el NAS ve el share de red en tiempo real (§1.1); el `git pull` se hace desde la máquina de trabajo.
- Hay otros proyectos del propietario corriendo en el NAS: no chocar con sus nombres de contenedor, puertos ni redes.
- El puerto `8000` del NAS lo ocupa un `nginx` interno de DSM (no es Docker); `buenchollo-api` usa `8001` en el host. No reutilizar `8000`.
- `scp` necesita la opción `-O` (protocolo SCP clásico; el NAS rechaza el subsistema SFTP moderno).
- Acciones locales y reversibles, sin pedir permiso. Acciones con impacto real (datos de producción, borrar volúmenes, tocar contenedores de otros proyectos): confirmar antes con el usuario.

## 1. Datos de conexión

| Campo | Valor |
|---|---|
| Modelo NAS | Synology DS224+ |
| Host | `<IP_NAS>` |
| Puerto SSH | `<PUERTO_SSH>` |
| Usuario | `<USUARIO_NAS>` (cuenta DSM del grupo `administrators`) |
| Clave privada (lado asistente/IA) | `~/.ssh/<CLAVE_SSH>` |
| Alias SSH | `<ALIAS_NAS>` |
| Binario Docker | `/volume1/@appstore/ContainerManager/usr/bin/docker` |
| Binario docker-compose | `/volume1/@appstore/ContainerManager/usr/bin/docker-compose` (Compose `v2.20.1`, clásico) |

La clave privada vive en la máquina desde la que trabaja la IA. La pública está autorizada en `~/.ssh/authorized_keys` del usuario en el NAS, y el usuario tiene `sudo` sin contraseña acotado a los dos binarios de Docker.

> 📌 El mismo host sirve **OmniRoute** en el puerto `20128` (ver [`ADR-013`](../adr/ADR-013-motor-ia-unificado-omniroute-modelos-gratuitos.md) y [`04-configuration.md`](../project/04-configuration.md)). Si SSH funciona pero `AI_BASE_URL=http://<IP_NAS>:20128/v1` no responde, el problema es del contenedor OmniRoute, no de la conectividad al NAS.

## 1.1 Caso concreto: `buenchollo-api` (este proyecto)

- **Ruta real en el NAS**: `<RUTA_SHARE>/BuenCholloTech/buenchollo-api` (se verifica con `docker inspect buenchollo-api --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'`). Es el **mismo recurso de red** que la unidad mapeada en la máquina de desarrollo: el código ya está ahí en tiempo real, sin `tar` ni `scp`. Reconstruir:
  ```bash
  DC="sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker-compose"
  ssh -o BatchMode=yes <ALIAS_NAS> "cd <RUTA_SHARE>/BuenCholloTech/buenchollo-api && $DC build && $DC up -d"
  ```
- Sin dependencias nuevas basta reiniciar: `ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER restart buenchollo-api buenchollo-scheduler"`. El procedimiento completo (backup, share en `main`, verificación y rollback) está en [`08-deployment.md`](../project/08-deployment.md).
- **⚠️ Trampa**: existe `/volume1/docker/buenchollo-auto/`, un proyecto **viejo y no relacionado** (bot de scraping con sesión de Telegram y SQLite). Una búsqueda de `docker-compose.yml` por el nombre lo encuentra y puede confundirse con el real: comprueba siempre que el `docker-compose.yml` define `buenchollo-api`, `buenchollo-scheduler` y `cloudflared`.
- **Rama del share**: los contenedores ejecutan la rama activa en el share en cuanto se reinician. Mantenerla en `main` (TD-31).
- **`.env` del NAS**: es independiente del local y está excluido del sync de SynologyDrive. Comprobar que `APP_ENV=production`: con `local`, la API acepta CORS desde `localhost:*` y no envía HSTS (incidente real de 2026-08-15, ver el histórico de [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Un `docker restart` no recarga el `env_file`; para aplicar cambios del `.env` usar `$DC up -d --force-recreate <servicio>`. No sobrescribirlo sin confirmar con el usuario qué variables cambian.

## 2. Configuración del cliente SSH (hecha en la máquina de trabajo)

En `~/.ssh/config`:

```
Host <ALIAS_NAS>
    HostName <IP_NAS>
    Port <PUERTO_SSH>
    User <USUARIO_NAS>
    IdentityFile ~/.ssh/<CLAVE_SSH>
    IdentitiesOnly yes
```

La clave se genera una sola vez con `ssh-keygen -t ed25519 -f ~/.ssh/<CLAVE_SSH> -N ""` y el usuario autoriza la pública en el NAS (nunca compartir la contraseña con la IA). El home del usuario SSH debe tener permisos `755`, no `777`, o `sshd` con `StrictModes` rechaza la clave.

El `sudo` acotado a Docker se configuró una única vez, con la contraseña del usuario:

```bash
echo '<USUARIO_NAS> ALL=(ALL) NOPASSWD: /volume1/@appstore/ContainerManager/usr/bin/docker, /volume1/@appstore/ContainerManager/usr/bin/docker-compose' | sudo tee /etc/sudoers.d/docker-nopasswd
sudo chmod 440 /etc/sudoers.d/docker-nopasswd
```

## 3. Verificar la conexión (siempre con BatchMode)

`BatchMode=yes` es obligatorio para una IA: si la clave falla, el comando falla al instante en lugar de quedarse pidiendo una contraseña.

```bash
ssh -o BatchMode=yes <ALIAS_NAS> "echo ok"                      # debe devolver: ok
ssh -o BatchMode=yes <ALIAS_NAS> "sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker ps"
```

Si alguno falla, **no continuar**: avisar al usuario, porque la clave o el `sudo` se han desincronizado.

## 4. Docker en este NAS

- `docker` no está en el `PATH` de una sesión SSH normal y no existe `docker compose`.
- El socket `/var/run/docker.sock` es solo root: por eso `sudo -n` con rutas completas. Los alias de shell no se cargan en sesiones SSH no interactivas.

```bash
DOCKER="sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker"
DC="sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker-compose"
```

## 5. Comandos operativos

```bash
ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER ps"                              # contenedores en marcha
ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER logs --tail 100 buenchollo-api"  # logs recientes
ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER logs --follow --tail 100 buenchollo-api"   # en vivo (Ctrl+C)
ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER restart buenchollo-api buenchollo-scheduler"
ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER inspect --format='{{.State.Health.Status}}' buenchollo-api"
ssh -o BatchMode=yes <ALIAS_NAS> "$DOCKER exec buenchollo-api alembic current"
```

Para ejecutar un script local dentro del contenedor sin reconstruir la imagen, pasarlo por stdin: `ssh ... "$DOCKER exec -i buenchollo-api python -" < script.py` (lanzarlo desde Bash; PowerShell añade BOM y CRLF).

Si el repositorio de otro proyecto del propietario necesita llegar al NAS sin share, el flujo es `tar` + `scp -O` + `docker-compose build/up`, excluyendo `.git`, `node_modules`, cachés y el `.env` (que se sube aparte y nunca se muestra).

## 6. Precauciones y trampas conocidas

1. **Puerto `8000` ocupado** por el `nginx` interno de DSM. Si otro servicio falla con `address already in use`, cambiar el puerto del host. Verificar con `$DOCKER ps` **y** con `wget -S -qO- --timeout=3 http://127.0.0.1:<puerto>/`, porque no todo lo que ocupa un puerto es un contenedor.
2. **No hay `git`**: nunca `git clone`/`git pull` en el NAS.
3. **`docker-compose` con guion** y **`scp -O`**.
4. **No pegar claves ni secretos en el chat ni en logs.**
5. **No tocar contenedores de otros proyectos** del propietario sin confirmación.

## 7. Si la conexión falla

1. Conectividad: `Test-NetConnection -ComputerName <IP_NAS> -Port <PUERTO_SSH>`.
2. Clave en modo estricto: `ssh -o BatchMode=yes -i ~/.ssh/<CLAVE_SSH> <USUARIO_NAS>@<IP_NAS> -p <PUERTO_SSH> "echo ok"`.
3. La clave pública sigue en `~/.ssh/authorized_keys` del NAS y el home es `755`: `ssh <ALIAS_NAS> "ls -ld ~ ~/.ssh ~/.ssh/authorized_keys"`.
4. El `sudo`: `ssh -o BatchMode=yes <ALIAS_NAS> "sudo -n /volume1/@appstore/ContainerManager/usr/bin/docker ps"`.
5. Si algo falla, **parar y avisar al usuario**; nunca adivinar contraseñas ni modificar permisos o `sudoers` del NAS.

---

<p align="center">
  <a href="Cloudflare.md">☁️ Guía Cloudflare</a> ·
  <a href="MIGRATIONS.md">🛠️ Guía Alembic</a> ·
  <a href="../project/00-index.md">📘 Operativa</a>
</p>
