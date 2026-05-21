# 🍄 BuenCholloTech

**BuenCholloTech** es una plataforma de publicación y gestión de ofertas tecnológicas desarrollada como **Proyecto de Fin de Máster en Desarrollo con IA (2025)**.

La plataforma integra scraping de Amazon, enriquecimiento automático con GPT-4o, panel de administración web y publicación en Telegram, sobre una arquitectura **API Gateway** con FastAPI + React.

---

## 🏗️ Arquitectura del sistema

El proyecto sigue el patrón **API Gateway**: el frontend solo habla con FastAPI, que actúa como única puerta de entrada a toda la lógica de negocio y seguridad.

```
Browser (React SPA)
        │
        ▼
 FastAPI — buenchollo-api       (Docker en NAS Synology)
        ├──► PostgreSQL (SQLAlchemy)  ← Supabase DB
        ├──► Supabase Auth            ← validación JWT
        ├──► Amazon Creators API      ← scraping de productos
        └──► OpenAI API               ← categorización y copy

 Excepción controlada:
 Browser ──► Supabase Storage   ← subida directa de imágenes (rendimiento)
```

> La migración desde BaaS directo (React → Supabase) al patrón API Gateway está justificada en [`docs/adr/ADR-002`](docs/adr/ADR-002-migracion-baas-a-api-gateway.md).

---

## 📦 Estructura del repositorio

| Directorio | Stack | Responsabilidad |
|---|---|---|
| `buenchollo-api/` | FastAPI + SQLAlchemy + Python 3.12+ | API Gateway: auth, BD, lógica de negocio |
| `buenchollo-web/` | React 18 + TypeScript + TanStack Router | SPA: UI pública y panel de administración |
| `API_Amazon_CloudCode/` | Python | **Solo referencia** — cliente Amazon funcional de ejemplo |

---

## 🛠️ Stack tecnológico

**Backend**
- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy async, Alembic
- Autenticación: JWT de Supabase Auth, validados por el backend con `require_admin`
- Tests: pytest + TestClient (integración real contra BD)

**Frontend**
- TypeScript, React 18, Vite, TanStack Router
- TailwindCSS + Shadcn/ui, Lucide Icons
- Capa de servicios API propia (`src/services/api/`) — sin llamadas directas a Supabase

**Infraestructura**
- BD: PostgreSQL gestionado con Supabase (pooler asyncpg, puerto 6543)
- Despliegue backend: Docker en NAS Synology (DDNS `embyZambu.synology.me`, HTTPS vía proxy inverso)
- IA: OpenAI GPT-4o (categorización semántica + copy de ventas)
- Scraping: Amazon Creators API v3.2
- Mensajería: Telegram Bot API

---

## 🚀 Inicio rápido

### Backend

```bash
cd buenchollo-api
cp .env.example .env       # Rellenar con credenciales reales
pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Swagger: `http://localhost:8000/docs`  
Health: `http://localhost:8000/health`

### Frontend

```bash
cd buenchollo-web
pnpm install
pnpm run dev               # http://localhost:5173
```

---

## 🔑 Variables de entorno clave (backend)

Ver [`buenchollo-api/.env.example`](buenchollo-api/.env.example) para la referencia completa.

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Conexión asyncpg al pooler de Supabase (puerto 6543) |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_KEY` | **Service role key** — no la anon key |
| `CORS_ORIGINS` | Orígenes CORS permitidos, separados por comas |
| `OPENAI_API_KEY` | Clave de OpenAI para enriquecimiento con IA |
| `AMAZON_CLIENT_ID / SECRET` | Credenciales Amazon Creators API |

---

## 🧪 Tests

```bash
cd buenchollo-api
python -m pytest app/tests/ -v
```

`test_deals_api.py` prueba el ciclo completo de administración (crear → actualizar → borrar chollo) contra la BD real de Supabase.

---

## 📖 Documentación

| Documento | Contenido |
|---|---|
| [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md) | Plan y estado de la migración BaaS → API Gateway |
| [`TODO.md`](TODO.md) | Roadmap de funcionalidades pendientes |
| [`docs/adr/ADR-002`](docs/adr/ADR-002-migracion-baas-a-api-gateway.md) | Decisión técnica: por qué API Gateway |
| [`docs/SUPABASE_SETUP.md`](docs/SUPABASE_SETUP.md) | Esquema de BD, auth y log de cambios |
| [`docs/UI_SYSTEM.md`](docs/UI_SYSTEM.md) | Sistema de iconografía dinámica |
| [`buenchollo-api/README.md`](buenchollo-api/README.md) | Documentación completa de la API |
| [`buenchollo-api/DEPLOY_NAS.md`](buenchollo-api/DEPLOY_NAS.md) | Guía de despliegue Docker en NAS |
| [`buenchollo-api/docs/NAS_DEPLOYMENT_ARCHITECTURE.md`](buenchollo-api/docs/NAS_DEPLOYMENT_ARCHITECTURE.md) | Arquitectura de infraestructura y red |

---

*Desarrollado por Pedro Zambudio — Máster en Desarrollo con IA 2025*
