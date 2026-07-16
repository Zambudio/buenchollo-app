# 🧾 10 · Deuda técnica

> **TL;DR** · Registro vivo de lo que falta o conviene mejorar **ahora mismo**.
> Solo items **abiertos**: cuando uno se cierra, se elimina de aquí (el histórico
> resuelto vive en [`PROJECT_STATUS.md`](../../PROJECT_STATUS.md)). Esta página es
> interna del proyecto; **no forma parte del bloque académico** ([`docs/master/`](../master/00-index.md)).

Última revisión: **2026-06-15** (auditoría final).

---

## 🔴 Alta — resolver antes de seguir creciendo

### TD-01 · Cifras de tests incoherentes entre documentos
La suite real no coincide entre fuentes: el badge raíz dice **167**, el de
`buenchollo-api/README.md` dice **97**, y el conteo bruto del backend (106 funciones
`def test_`, ~97 sin integración) apunta a un total real ≈ **177**.

- **Verificado:** frontend = **72** Vitest + **8** E2E.
- **Bloqueo:** no se pudo correr `pytest` para fijar el backend (el entorno de la
  auditoría tenía Python 3.14; el proyecto y el CI usan **3.11**).
- **Acción:** correr bajo Python 3.11 y propagar **una** cifra a todos los sitios:
  ```bash
  cd buenchollo-api && pytest -q && pytest -q -m "not integration"
  ```
  Actualizar: `README.md` (badge + sección tests), `buenchollo-api/README.md` (badge),
  `docs/project/06-testing-and-quality.md` y `docs/master/06-...`.

### TD-02 · `CORS_ORIGINS` rompe el arranque con formato CSV
`core/config.py` define un `field_validator` que parte por comas, pero
`pydantic-settings` **pre-parsea los campos de tipo lista como JSON antes** de que
corra el validator. Por eso una cadena CSV plana (`a.com,b.com`) revienta el arranque
y hoy se exige **formato JSON array** (`["a.com","b.com"]`).

- **Acción:** tipar `cors_origins` como `str` y parsear en una propiedad/validador, o
  configurar el decoding, de modo que acepte CSV. Alinear `.env.example` (hoy muestra
  CSV, que fallaría).

---

## 🟡 Media — mejora de mantenibilidad

### TD-03 · God Component `admin.chollos.tsx` (≈986 líneas)
Mezcla UI + lógica de negocio + 13 estados; sin tests unitarios dedicados (se cubre
vía E2E/smoke). Es el punto más atacable en SRP.
- **Acción:** extraer hooks (`useAdminDeals`, `useDealForm`) y subcomponentes de
  formulario/listado. Mientras tanto, queda registrado aquí como deuda consciente.

### TD-04 · Capas `application/` incompletas en módulos menores
`categories/` y `stores/` van `router → repository` sin capa de aplicación.
Aceptable para CRUD simple, pero inconsistente con la arquitectura declarada.
Revisar también `users/` (PROJECT_STATUS tiene afirmaciones contradictorias sobre si
ya tiene capa de uso).

### TD-05 · `__init__.py` faltantes en subdirectorios de módulos
Funciona por namespace packages, pero da problemas con linters/IDEs/herramientas de
test. Faltan en varios subdirectorios de `deals/`, `categories/`, `stores/`, `users/`,
`telegram/api/`.

### TD-06 · Excepciones de dominio incompletas
No todos los módulos tienen excepciones de dominio propias; varios routers lanzan
`HTTPException` directa, mezclando protocolo HTTP con lógica de negocio.

### TD-07 · Tests de integración no corren en CI
Los marcados `@pytest.mark.integration` solo se ejecutan en local (requieren Postgres
real). Migrar a CI con un servicio Postgres para cubrirlos automáticamente.

### TD-11 · Latencia general al cargar chollos (home y detalle)
Home y `/chollo/:slug` tardan varios segundos en cargar en producción. Diagnosticado
2026-07-09: el waterfall duplicado del detalle ya se corrigió (fetch SSR+CSR
redundante + relacionados bloqueando el render), y se añadieron índices compuestos
`(status, published_at)` / `(status, temperature)` en `deals` (ya aplicados en BD),
pero con solo ~117 filas ese índice apenas influye — el grueso sigue siendo:
- El contenedor `uvicorn` del NAS corre **sin `--workers`** (proceso único) detrás de
  Cloudflare Tunnel: cada request paga el salto NAS↔Tunnel↔cliente en serie.
- No se ha medido el pool de conexiones SQLAlchemy async contra el pooler PgBouncer
  (puerto 6543, modo transacción) — posible latencia extra de conexión por request.
- **Acción:** revisar `--workers` de uvicorn en `docker-compose.yml`/`Dockerfile`,
  medir tiempos reales con el NAS bajo carga normal, y decidir si compensa mover
  algo de I/O (imágenes) a un CDN o cache.

---

## 🟢 Baja — pulido

### TD-08 · `console.error` en rutas frontend
8 ocurrencias en rutas (`chollo.$slug.tsx`, `explorar.tsx`, `favoritos.tsx`,
`categorias.tsx`, `index.tsx`, `CategoriesDrawer.tsx`). Enrutar a un logger central o
justificar por qué se dejan.

### TD-09 · Telegram aún usa Supabase Functions
Pendiente migrar a `POST /telegram/notify` en el backend (coherencia con ADR-002).

### TD-10 · Estado real de ADR-002 por reconciliar
`README.md` afirma "ADR-002 100% cumplido" pero `CLAUDE.md` menciona "4 rutas
restantes". Verificar el estado real y dejar una única afirmación coherente.

---

> 🔁 **Cómo usar esta página:** revisar al empezar cada tanda de trabajo. Al cerrar un
> item, borrar su entrada y anotar el cierre (fecha + commit) en `PROJECT_STATUS.md`.
