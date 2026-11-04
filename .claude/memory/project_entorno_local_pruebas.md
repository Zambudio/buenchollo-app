---
title: "Entorno local de pruebas (local-env/) aislado de producción"
category: "environment"
date: "2026-11-04"
status: "active"
---

# Entorno local de pruebas

- **Existe y es el camino para probar antes de desplegar**:
  `.\local-env\bct-local.cmd setup` (una vez por PC) → `start` → web en
  `http://localhost:8080`, API `:8000`, correos `:8025`. Guía completa:
  [`docs/guides/LOCAL-ENV.md`](../../docs/guides/LOCAL-ENV.md).
- **Base de datos local** (PostgreSQL 17 portable en `%LOCALAPPDATA%\BuenCholloLocal`,
  puerto 54329): esquema = `pg_dump` del esquema real de producción + `alembic upgrade
  head`; datos = copia de solo lectura del catálogo. **No** reproducir
  `supabase/migrations/*.sql`: no coinciden con producción (TD-36).
- **Sigue siendo real**: Supabase Auth (cuentas), Supabase Storage (imágenes) y Amazon
  Creators API. El scheduler va **apagado** a propósito: su limpieza usa Supabase REST =
  producción (TD-37). Telegram apagado, correo capturado en local.
- **Usuarios de prueba**: `bct-local.cmd users create 6` (alias
  `pjzambudio+local-N@gmail.com`, credenciales en `%LOCALAPPDATA%\BuenCholloLocal\test-users.json`);
  `users delete` al acabar. **No** escribir esas credenciales en el login de la web
  (va al Supabase real): las pruebas con sesión van por API (`local-env/qa/`).
- **Pruebas en vivo**: `bct-local.cmd qa` (pytest, ~165 casos, ~8 min por rate limits) y
  `bct-local.cmd stress`. El usuario de prueba nº 1 es admin solo en la base local.
- **Trampas resueltas**: Windows App Control bloquea Mailpit y `uuid-ossp.dll` (se usa un
  capturador SMTP en Python); Vite no admite rutas UNC (el lanzador usa `Z:`, nunca `N:`,
  ver [[project_entorno_local_nas_drive]]); `Start-Process` con salida canalizada cuelga
  (se lanza con `py/spawn.py`); contraseña con `€` corrompida por variables de entorno
  (pgpass UTF-8 temporal).
- **No cambiar de rama en el share del NAS para probar** (TD-31): clonar en disco local.
