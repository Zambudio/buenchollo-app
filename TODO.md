# 📝 Hoja de Ruta — BuenCholloTech

Roadmap de funcionalidades y tareas técnicas pendientes del proyecto.

> Para el estado de la migración arquitectónica BaaS → API Gateway, ver [`REFACTOR_PLAN.md`](REFACTOR_PLAN.md).

---

## 🚀 Prioridad Alta

### 1. Verificar y estabilizar el Panel de Administración
- [ ] **Probar en producción** el flujo completo de guardar chollos tras el redeploy en el NAS (validación de JWT + `has_role()` + FK `created_by`).
- [ ] **Diagnóstico con `/auth/me`**: Si falla, llamar a `GET /auth/me` con sesión iniciada para confirmar que el JWT llega al backend y que `is_admin` es `true`.
- [ ] **Revisar `SUPABASE_KEY`** en el `.env` del NAS: debe ser la `service_role` key, no la `anon` key.

### 2. Telegram — migrar a FastAPI
- [ ] Mover la lógica de `notify-telegram` (actualmente en Supabase Functions) a un endpoint en FastAPI: `POST /telegram/notify`.
- [ ] Eliminar la llamada directa a `supabase.functions.invoke("notify-telegram")` del frontend.
- [ ] Crear un módulo `app/modules/telegram/` con el caso de uso y el cliente de Telegram.

### 3. Tests
- [ ] Añadir tests unitarios para `PreviewProductFromUrlUseCase` con mocks de los nuevos Protocols (`CategoryClient`, `AIEnricher`).
- [ ] Añadir tests de integración para los endpoints de categorías y tiendas.
- [ ] Configurar un entorno de test separado para no afectar datos de producción.

---

## 📅 Funcionalidades Pendientes

### Panel de Admin
- [ ] **Gestión de Tiendas**: CRUD de tiendas desde el panel admin (actualmente solo se pueden ver).
- [ ] **Ordenación drag & drop**: Reordenar chollos en el listado admin.

### Scheduling de chollos
- [ ] El scheduler ya existe (limpieza de caducados). Añadir la activación automática de chollos `scheduled` cuando llegue la fecha de `scheduled_for`.
- [ ] Publicación diferida en Telegram cuando un chollo pasa de `scheduled` a `active`.

### Funcionalidades de usuario
- [ ] **Sistema de votos**: Activar la lógica de temperatura desde el frontend (endpoint ya preparado en la BD).
- [ ] **Favoritos**: Endpoint en FastAPI para gestionar los favoritos de cada usuario.
- [ ] **Vista de Tiendas**: Página pública con logos y chollos activos por tienda.

---

## 🏗️ Deuda técnica

- [ ] **Alembic**: Configurar migraciones de Alembic para gestionar cambios de esquema desde el backend (actualmente el esquema se gestiona solo desde Supabase).
- [ ] **CI/CD**: Automatizar el build y despliegue al NAS (actualmente es un proceso manual de copiar archivos).
- [x] **ADR-001**: Creado `docs/adr/ADR-001-monolito-modular-fastapi.md`.
- [ ] **Frontend**: Eliminar los últimos usos directos de `supabase.from()` que queden fuera del panel admin.

---

## ✅ Completado recientemente

- [x] Migración completa del panel de admin a FastAPI (CRUD chollos y categorías).
- [x] Endpoints públicos de lectura (chollos, categorías, tiendas) migrados a FastAPI.
- [x] SQLAlchemy + modelos de dominio (Deal, Category, Store, Profile).
- [x] Autenticación JWT con `require_admin` (Supabase Auth + tabla `user_roles`).
- [x] DIP en `PreviewProductFromUrlUseCase` — Protocols `CategoryClient` y `AIEnricher`.
- [x] Scheduler con `lifespan` de FastAPI (limpieza diaria de chollos caducados).
- [x] CORS configurable por variable de entorno (`CORS_ORIGINS`).
- [x] `.env.example` completo y documentado.
- [x] Endpoint de diagnóstico `GET /auth/me`.
- [x] ADR-002: Decisión de arquitectura BaaS → API Gateway.
- [x] Sincronización de categorías con Supabase para el prompt de IA.
- [x] Integración OpenAI (GPT-4o) para categorización y copy.
- [x] Autocompletar desde Amazon en el panel admin (título, precio, imágenes, marca).

---

*Última actualización: 19 de Mayo de 2026*
