# Entorno local de pruebas (`local-env/`)

> **TL;DR** · `.\local-env\bct-local.cmd setup` (una vez por PC) ·
> `.\local-env\bct-local.cmd start` · abre <http://localhost:8080> ·
> correos en <http://localhost:8025> · `.\local-env\bct-local.cmd stop`.
> Web + API + Postgres + correo en tu PC, con la rama que tengas activa,
> **sin tocar la base de datos de producción**. Sin Docker.

Sirve para probar a mano (y con pruebas automáticas en vivo) cualquier
cambio antes de desplegarlo: navegas por `localhost` como si fuera la web
real, con el catálogo real copiado, tu cuenta de siempre (con rol admin) y
todos los correos capturados en local.

---

## 1. Qué es local y qué sigue siendo real

| Pieza | En el entorno local | Notas |
|---|---|---|
| Base de datos | **Local** (PostgreSQL 17 portable, puerto `54329`) | Esquema = volcado del esquema **real** de producción + migraciones pendientes de tu rama. Datos = copia del catálogo (tiendas, categorías, chollos, blog, programados). |
| API | **Local** (`uvicorn` en `:8000`, recarga al editar `app/`) | Mismo código que la rama activa. |
| Web | **Local** (Vite dev en `:8080`) | Llama a la API local. |
| Correo | **Local** (capturador en `:1025` SMTP / `:8025` web) | Nada sale a Internet. |
| Scheduler | **Apagado** | Su limpieza usa la API REST de Supabase = **producción**. Nunca encenderlo en local. |
| Telegram | **Apagado** (tokens vacíos) | Aprobar con "publicar en Telegram" no publica nada. |
| Login (Supabase Auth) | ⚠️ **Real** | Mismas cuentas que en producción. |
| Imágenes (Supabase Storage) | ⚠️ **Real** | Las que subas van al bucket real `deal-images`. |
| Amazon Creators API | ⚠️ **Real** (solo lecturas) | El autorrelleno de Amazon funciona de verdad. |

**Cuidado con lo real**

- **Borrar la cuenta** desde la web local borra la cuenta **real** de
  Supabase Auth. Hazlo solo con usuarios de prueba.
- Las imágenes que subas (propuestas, panel admin, avatar) quedan en el
  Storage real. Las de propuestas de usuarios de prueba se borran con
  `users delete` (§5); las del panel admin y avatares, a mano.
- Registrarte en la web local crea una cuenta **real**. Usa alias
  `pjzambudio+algo@gmail.com`.

## 2. Requisitos

- Windows 10/11 (los scripts son PowerShell; probados con Windows PowerShell 5.1).
- Python **3.11+** instalado con el *py launcher* (`py -3.11`). Recomendado 3.11, el de producción.
- Node **20+** y Git.
- Internet: descarga PostgreSQL 17 portable (~330 MB, una vez), y en cada
  `setup`/`reset-db` lee el esquema y el catálogo de producción (solo lectura).
- Los dos ficheros de secretos (no están en Git):
  `buenchollo-api/.env` y `buenchollo-web/.env`.

No hace falta Docker, ni instalar PostgreSQL, ni permisos de administrador.

## 3. Primer uso en este PC

El repo de este PC está en el share del NAS
(`\\Zambu-nas\nas-drive-pedro\IA\02_Proyectos\WEB-Buenchollo\BuenCholloTech`,
también como unidad `Z:`) y los `.env` ya están ahí.

```powershell
cd Z:\IA\02_Proyectos\WEB-Buenchollo\BuenCholloTech
.\local-env\bct-local.cmd setup     # instala todo y monta la base local (5-10 min la 1ª vez)
.\local-env\bct-local.cmd start     # levanta todo (la 1ª carga de la web tarda ~30 s)
```

`bct-local.cmd` llama a `bct-local.ps1` con `-ExecutionPolicy Bypass`, así
que funciona aunque la política de PowerShell del PC bloquee scripts.

## 4. Otro PC

1. Instala Python 3.11 (python.org, marca "py launcher"), Node 20+ y Git.
2. **Clona el repo en un disco local** (no en el share del NAS, ver §8):
   ```powershell
   git clone https://github.com/Zambudio/buenchollo-app.git C:\dev\buenchollo-app
   cd C:\dev\buenchollo-app
   git checkout develop
   ```
3. Copia los secretos desde el NAS (mismas rutas relativas):
   ```powershell
   $nas = '\\Zambu-nas\nas-drive-pedro\IA\02_Proyectos\WEB-Buenchollo\BuenCholloTech'
   Copy-Item "$nas\buenchollo-api\.env" .\buenchollo-api\.env
   Copy-Item "$nas\buenchollo-web\.env" .\buenchollo-web\.env
   ```
   Fuera de casa: pídelos al propietario. Nunca los subas a Git ni los pegues en chats.
4. `.\local-env\bct-local.cmd setup` y `.\local-env\bct-local.cmd start`.

Si otra persona va a usarlo con su propia cuenta admin, crea
`local-env/config.local.json` (ignorado por Git) con
`{"admin_emails": ["su-correo@gmail.com"], "sync_email_patterns": ["su-correo+*@gmail.com"], "test_email_template": "su-correo+local-{n}@gmail.com"}`
y ejecuta `reset-db`.

## 5. Uso diario

| Comando (`.\local-env\bct-local.cmd …`) | Qué hace |
|---|---|
| `start` | Levanta Postgres, correo, sincronizador de usuarios, API y web. `-NoWeb` sin web; `-NoReload` sin recarga de la API. |
| `stop` | Para todo (por PID; nunca mata otros `python`/`node` del PC). |
| `restart` | `stop` + `start`. |
| `status` | Qué está levantado y sus URLs. |
| `logs api` | Últimas líneas del log (`postgres`, `mail`, `authsync`, `api`, `web`). |
| `reset-db` | Borra la base local y la reconstruye con el esquema y el catálogo **actuales** de producción. |
| `users create 6` | Crea usuarios de prueba reales `pjzambudio+local-N@gmail.com` (confirmados, contraseña aleatoria). |
| `users tokens` | Imprime sus access tokens (JSON). |
| `users delete` | Borra los usuarios de prueba de Supabase Auth y sus imágenes de propuestas en Storage. |
| `qa` | Lanza la batería de pruebas en vivo (§7). |
| `stress` | Lanza la prueba de estrés (§7). |

URLs: web <http://localhost:8080> · API <http://localhost:8000/docs> ·
correos <http://localhost:8025>.

**Entrar en la web local**

- **Con tu cuenta** (correo y contraseña o Google): en local tienes rol
  admin (`/admin`, `/admin/propuestas`).
- **Con un usuario de prueba**: credenciales en
  `%LOCALAPPDATA%\BuenCholloLocal\test-users.json`.
- **Registrándote**: cualquier cuenta creada después de montar la base local
  aparece en local en ~3 s (la refleja el sincronizador). Usa un alias.
- Google OAuth desde `localhost` necesita `http://localhost:8080/**` en
  *Supabase → Authentication → URL Configuration → Redirect URLs*. Si no
  está, el login por correo y contraseña funciona igual.

## 6. Cómo funciona por dentro

```
local-env/
├── bct-local.ps1 / .cmd   ← lanzador (setup, start, stop, …)
├── config.json            ← admins, alias de prueba, tablas a copiar, puertos
├── requirements.txt       ← deps del venv (las de la API + aiosmtpd)
├── sql/supabase_shim.sql  ← roles, schema extensions, auth.users, auth.uid(), storage
├── py/
│   ├── common.py          ← rutas y config compartidas
│   ├── db_setup.py        ← recrea la base local
│   ├── auth_sync.py       ← refleja usuarios de Supabase Auth en la base local
│   ├── mail_catcher.py    ← SMTP + web de correos
│   ├── spawn.py           ← lanza procesos desacoplados
│   └── test_users.py      ← usuarios de prueba
└── qa/                    ← pruebas en vivo y estrés contra el entorno local
```

Todo el estado de máquina vive **fuera del repo**, en
`%LOCALAPPDATA%\BuenCholloLocal\` (o `BCT_LOCAL_HOME`): `pgsql\` (binarios),
`pgdata\` (datos), `api-venv\`, `logs\`, `pids\`, `mail\`, `state.json`,
`test-users.json`.

**Base de datos** (`db_setup.py`):

1. Recrea `buenchollo_local` (locale ICU `en-US`, igual que producción).
2. Aplica `supabase_shim.sql`: lo que Supabase trae de serie y el esquema
   referencia.
3. `pg_dump --schema-only --schema=public` de **producción** (conexión en solo
   lectura) y lo restaura. **No** se reproducen
   `buenchollo-api/supabase/migrations/*.sql`: no coinciden con producción
   (allí los enums son `text`, no existen sus triggers, etc.; ver TD-36).
4. Crea el trigger `on_auth_user_created` sobre `auth.users`, como en producción.
5. Refleja las cuentas permitidas (`auth_sync.sync_once`).
6. Copia en solo lectura las tablas de `snapshot_tables`, `alembic_version` y
   el perfil/roles de los admins. Las referencias a usuarios no copiados se
   anulan. **No** se copian comentarios, votos, favoritos, alertas,
   notificaciones, analítica ni perfiles de otros usuarios.
7. `alembic upgrade head`: aplica las migraciones de tu rama que aún no estén
   en producción, igual que hará el contenedor al desplegar.

**Usuarios** (`auth_sync.py`, cada 3 s): la web hace login contra el Supabase
Auth real y la API local valida el JWT con la clave pública de Supabase, pero
busca perfil y roles en la base local. El sincronizador inserta en la tabla
local `auth.users` las cuentas permitidas (admins de `config.json`, alias de
prueba y cualquier cuenta creada después de montar la base) y el trigger de
producción crea su perfil. Las cuentas borradas en Supabase se borran en local.

**Variables de la API**: el lanzador reutiliza `buenchollo-api/.env`
(credenciales de Supabase y Amazon) pero sobrescribe por entorno
`DATABASE_URL`, `APP_ENV=local`, `SCHEDULER_ENABLED=false`, `SMTP_*`,
`TELEGRAM_*` y `CORS_ORIGINS` (ver `Get-ApiEnv` en `bct-local.ps1`). El `.env`
no se modifica.

## 7. Pruebas contra el entorno local

```powershell
.\local-env\bct-local.cmd users create 6   # una vez
.\local-env\bct-local.cmd qa               # batería en vivo (≈10-15 min por los rate limits)
.\local-env\bct-local.cmd stress           # estrés: concurrencia, carreras, ráfagas
```

- `local-env/qa/test_*.py` (pytest): acceso y tokens falsos, todo lo que un
  usuario puede pegar mal en el enlace, subida de imágenes (formatos, bombas
  de descompresión, SSRF en "imagen desde URL"), validación del formulario,
  duplicados, cupos, "mis chollos", moderación (aprobar, rechazar, dobles
  clics y carreras entre admins, sustitución de caducados, correos y
  notificaciones) y rate limits.
- El usuario de prueba nº 1 recibe rol admin **solo en la base local**
  durante la batería. Todo lo que crean las pruebas se borra al terminar.
- Las suites de siempre siguen igual (`pytest` en `buenchollo-api`,
  `npm run test:run` y `npm run test:e2e` en `buenchollo-web`). Con el entorno
  levantado, Playwright choca con el puerto 8080: usa
  `$env:PLAYWRIGHT_PORT=8090; npm run test:e2e`. Sobre el share, Vite tarda en
  frío más que los 120 s que Playwright espera al servidor: arranca antes
  `node node_modules/vite/bin/vite.js dev` en ese puerto y lanza Playwright con
  `reuseExistingServer: true` (o ejecútalo desde un clon local).
- Los tests de integración del backend pueden usar el mismo Postgres local con una
  base aparte:
  ```powershell
  $pg = "$env:LOCALAPPDATA\BuenCholloLocal\pgsql\bin\psql.exe"
  & $pg -h 127.0.0.1 -p 54329 -U postgres -c "DROP DATABASE IF EXISTS buenchollo_test WITH (FORCE)" -c "CREATE DATABASE buenchollo_test"
  cd buenchollo-api
  $env:DATABASE_URL = 'postgresql+asyncpg://postgres@127.0.0.1:54329/buenchollo_test'
  & "$env:LOCALAPPDATA\BuenCholloLocal\api-venv\Scripts\python.exe" scripts/create_test_schema.py
  & "$env:LOCALAPPDATA\BuenCholloLocal\api-venv\Scripts\python.exe" -m pytest -m integration
  ```
  Recréala antes de cada pasada: los tests dejan datos.

## 8. Avisos importantes

- **El NAS ejecuta la copia de trabajo del share.** Los contenedores de
  producción montan `\\Zambu-nas\...\BuenCholloTech` (TD-31): la rama activa
  ahí es lo que producción carga al reiniciarse. **No cambies de rama en el
  share para probar otra cosa**: clona el repo en un disco local (§4) y prueba
  allí. El entorno local en sí no afecta a los contenedores.
- **Probar otra rama** (en un clon local): `git checkout <rama>`, después
  `reset-db` si trae migraciones (se aplican con `alembic upgrade head`) y
  `restart`.
- El entorno no ejecuta tareas programadas: los chollos no caducan ni se
  activan solos. Cambia `status`/`expires_at` en la base local si lo necesitas
  (`pgsql\bin\psql.exe -h 127.0.0.1 -p 54329 -U postgres buenchollo_local`).

## 9. Problemas conocidos y solución

| Síntoma | Causa | Solución |
|---|---|---|
| "Una directiva de Control de aplicaciones bloqueó este archivo" | Windows App Control bloquea binarios sin firmar | Por eso no se usa Mailpit ni `uuid-ossp`. Si bloquea otra DLL de Postgres, apúntalo aquí. |
| La web no arranca: *Failed to resolve entry for package "vite"* | Vite no admite rutas UNC | El lanzador usa la letra de unidad mapeada (`Z:`) o mapea una libre. Comprueba `logs web`. |
| `pg_dump: password authentication failed` | Contraseña de la BD con caracteres no ASCII | Ya resuelto (pgpass temporal UTF-8). Si vuelve a pasar, revisa `DATABASE_URL` del `.env`. |
| 403 "completa tu perfil" justo tras registrarte | El sincronizador aún no ha reflejado la cuenta | Espera ~3 s y recarga. `logs authsync`. |
| Puerto ocupado | Otro proceso en `8000`/`8080`/`54329`/`1025`/`8025` | Cambia puertos en `config.local.json` (`api_port`, `web_port`, …). |
| La 1ª carga de la web tarda ~30 s | Vite compila en frío sobre el share | Normal; las siguientes son rápidas. En un clon local es más rápido. |
| La API no recoge los cambios del código | En shares SMB no llegan eventos de cambio | Ya resuelto: el lanzador pone `WATCHFILES_FORCE_POLLING=true` (tarda ~1 s en detectar). Si dudas, `restart`. |
| `psql`: *invalid byte sequence for encoding "UTF8"* | La consola usa la página de códigos de Windows | `$env:PGCLIENTENCODING='UTF8'` antes de `psql`. |

**Desinstalar**: `stop` y borrar `%LOCALAPPDATA%\BuenCholloLocal`.
