# Migraciones — buenchollo-api

Este proyecto usa **dos formatos de migración** que conviven por razones
históricas:

| Formato | Ubicación | Cuándo se usa | Qué gestiona |
|---|---|---|---|
| **SQL puro** (Supabase) | `buenchollo-api/supabase/migrations/*.sql` | 2026-04 → 2026-05 (legado) | Esquema inicial, triggers, funciones, policies RLS. |
| **Alembic** (SQLAlchemy) | `buenchollo-api/alembic/versions/*.py` | Desde 2026-05-27 en adelante | Cambios al esquema gestionados desde el código Python. |

La migración `20260527120000_baseline.py` es **vacía** y marca el punto donde
los dos formatos se encuentran: todo lo anterior se aplicó vía SQL (ya
presente en producción), todo lo posterior se genera y se aplica con Alembic.

---

## Setup inicial (una sola vez)

Si tu BD ya está vivía (caso normal en BuenChollo), hay dos vías para
sincronizar Alembic con su estado actual.

### Vía A — Tienes acceso shell a la BD/contenedor

```bash
cd buenchollo-api
source .venv/bin/activate    # o el equivalente en tu sistema

# Marca la baseline como aplicada SIN ejecutar SQL
alembic stamp head
```

### Vía B — Sólo tienes acceso al SQL Editor (caso BuenChollo en NAS)

Ejecuta este SQL contra la BD:

```sql
CREATE TABLE IF NOT EXISTS public.alembic_version (
    version_num VARCHAR(32) NOT NULL,
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

TRUNCATE public.alembic_version;
INSERT INTO public.alembic_version (version_num) VALUES ('<rev_actual>');
```

Sustituye `<rev_actual>` por el último `revision` del fichero más reciente
en `alembic/versions/`. Tras esto el contenedor (que ejecuta
`alembic upgrade head` al arrancar — ver `docker-compose.yml`) ya no
intentará aplicar nada porque la versión está al día.

## Despliegue automático de migraciones

`docker-compose.yml` ejecuta `alembic upgrade head` justo antes de uvicorn,
así cualquier migración nueva se aplica al reiniciar el contenedor.
**Si la migración falla, el contenedor no arranca**: intencional para no
correr con esquema obsoleto.

---

## Flujo diario: añadir / cambiar una tabla

1. **Modificar el modelo** SQLAlchemy en `app/modules/<modulo>/domain/models.py`.

2. **Si el modelo es nuevo**, importarlo en `app/core/base.py` para que
   Alembic lo registre.

3. **Generar la migración**:

   ```bash
   alembic revision --autogenerate -m "add_<descripcion_corta>"
   ```

   Alembic generará un fichero `alembic/versions/<rev>_add_<...>.py` con los
   cambios detectados.

4. **REVISAR el fichero generado**. Alembic acierta con tablas/columnas pero:
   - Ignora triggers, funciones SQL y policies RLS — si los necesitas,
     añádelos a mano con `op.execute("CREATE TRIGGER ...")`.
   - No detecta `enum`s nuevos en Postgres sin ayuda; usa
     `op.execute("CREATE TYPE ...")` si hace falta.
   - Verifica que no genera drops inesperados (filtro `include_object`
     ya excluye `user_roles`, `import_logs` y schemas externos).

5. **Aplicar** localmente:

   ```bash
   alembic upgrade head
   ```

6. **Verificar** que la app sigue arrancando y los tests pasan:

   ```bash
   uvicorn app.main:app --reload     # smoke check
   pytest                            # test suite
   ```

7. **Commit** del modelo + la migración juntos.

8. En **producción** (NAS): tras `git pull` ejecutar
   `docker exec -it buenchollo-api alembic upgrade head` antes de reiniciar
   el servicio.

---

## Reglas de oro

- **El modelo SQLAlchemy es la fuente de verdad** del esquema desde
  2026-05-27. Cambios manuales en la BD (via SQL Editor de Supabase) están
  prohibidos en producción excepto:
  - Hotfixes de seguridad (documentar inmediatamente).
  - Operaciones admin puntuales (ej. promote a admin).
- **Una migración = un commit**. No agrupar varios cambios en una migración
  salvo que estén tan relacionados que no tenga sentido separarlos.
- **Las migraciones son irreversibles en producción** salvo emergencia.
  Por eso `downgrade()` se mantiene completo en caso de rollback.
- **Tablas legacy sin modelo** (`user_roles`, `import_logs`) viven en el
  set `_LEGACY_TABLES_NOT_MODELED` de `alembic/env.py`. Si en el futuro se
  modelan en SQLAlchemy, eliminar la entrada y declararlas en `base.py`.

---

## Troubleshooting

### Alembic genera drops de tablas que sí quiero mantener
Comprueba que esas tablas tienen modelo registrado en `app/core/base.py`.
Si no quieres modelarlas, añádelas a `_LEGACY_TABLES_NOT_MODELED` en
`alembic/env.py`.

### Alembic no detecta un cambio que sí hice
- ¿El modelo está importado en `app/core/base.py`?
- ¿El cambio es sobre tabla en schema `public`? Cualquier otro schema
  está ignorado por diseño.
- Si es un trigger / función / policy: Alembic no las detecta. Hay que
  añadir `op.execute("...")` manual a la migración.

### `alembic upgrade head` falla con "table already exists"
Significa que la baseline no está stampada. Ejecuta:

```bash
alembic stamp head
```

(asumiendo que tu BD ya tiene el esquema aplicado).

### Quiero rehacer todo desde cero en local
```bash
alembic downgrade base    # revierte todas las migraciones Alembic
# (No revierte las SQL legacy de supabase/migrations/)
```

Para reinicio completo, recrear la BD desde Supabase Dashboard.
