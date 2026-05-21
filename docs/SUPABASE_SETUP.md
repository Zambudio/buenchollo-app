# Configuración: Supabase & Base de Datos

Este documento detalla la configuración de la base de datos, la autenticación y los cambios de esquema del proyecto **BuenCholloTech**.

---

## 🏗️ Rol de Supabase en la arquitectura

Supabase provee tres servicios que el proyecto usa de forma diferenciada:

| Servicio | Usado por | Descripción |
|---|---|---|
| **PostgreSQL** | Backend (FastAPI vía SQLAlchemy) | Fuente de verdad de todos los datos |
| **Auth** | Backend (valida JWT) / Frontend (sesión) | Google OAuth, emisión de tokens JWT |
| **Storage** | Frontend (directo) | Subida de imágenes de chollos |

> A partir de la Fase 3 de la refactorización (mayo 2026), el frontend ya no hace consultas directas a la BD. Toda la lógica de negocio pasa por FastAPI. Ver [ADR-002](adr/ADR-002-migracion-baas-a-api-gateway.md).

---

## 🔐 Autenticación (Google OAuth)

### Configuración realizada
1. **Google Cloud Console**: Proyecto con credenciales OAuth 2.0 (Client ID + Client Secret).
2. **Redirect URIs**: `http://localhost:8080` (desarrollo) y el dominio de producción.
3. **Supabase Auth**: Proveedor Google activado con las credenciales del paso anterior.
4. **Frontend**: Usa `supabase.auth.signInWithOAuth({ provider: "google" })`.
5. **Backend**: Valida el JWT emitido por Supabase con `supabase.auth.get_user(token)` usando la **service_role key**.

### ⚠️ SUPABASE_KEY en el backend

El backend necesita la **service_role key** (no la anon key) para poder llamar a `auth.get_user()` sin restricciones de RLS. La anon key solo permite operaciones que el usuario podría hacer directamente.

```env
# backend/.env
SUPABASE_KEY=eyJ...service_role_key...   # Empieza igual pero tiene "role":"service_role" en el payload JWT
```

---

## 📊 Esquema de base de datos (v2.0)

Esquema reconstruido el 15 de mayo de 2026 para soportar funcionalidades avanzadas. Los modelos SQLAlchemy en el backend replican este esquema.

### Tablas principales

| Tabla | SQLAlchemy Model | Propósito |
|---|---|---|
| `profiles` | `app/modules/users/domain/models.py` | Perfil extendido de usuario (username, avatar, bio) |
| `user_roles` | — (consulta raw SQL) | Roles por usuario (`admin`, `user`). Función `has_role()` |
| `deals` | `app/modules/deals/domain/models.py` | Chollos: precios, descuentos, imágenes, estado |
| `categories` | `app/modules/categories/domain/models.py` | Categorías y subcategorías (jerárquico con `parent_id`) |
| `stores` | `app/modules/stores/domain/models.py` | Tiendas con logo y datos de afiliación |
| `deal_comments` | — (pendiente) | Comentarios anidados (`parent_id`) |
| `deal_votes` | — (pendiente) | Votos de temperatura (UNIQUE por usuario + chollo) |

### Relaciones clave
- Un `deal` pertenece a una `store` y a una `category` (con `subcategory` opcional).
- `deals.created_by` → FK a `profiles.user_id` (SET NULL si se borra el perfil).
- Los `deal_votes` tienen restricción `UNIQUE (user_id, deal_id)`.

### Enum `app_role`
La tabla `user_roles` usa el tipo enumerado PostgreSQL `app_role` con valores `'admin'` y `'user'`.  
La función SQL `has_role(_role app_role, _user_id uuid) → boolean` es la forma idiomática de comprobar roles.

---

## 🔧 Conexión a la BD desde el backend

El backend usa **asyncpg** vía SQLAlchemy con el pooler de transacciones de Supabase:

```env
DATABASE_URL=postgresql+asyncpg://postgres.[ref]:[password]@aws-0-eu-central-1.pooler.supabase.com:6543/postgres
```

**Configuración crítica** para compatibilidad con PgBouncer en modo transacción:
```python
connect_args={"server_settings": {"jit": "off"}, "statement_cache_size": 0}
```

Sin `statement_cache_size=0`, asyncpg falla con PgBouncer porque intenta usar prepared statements de sesión que PgBouncer no soporta en modo transacción.

---

## 🛠️ Log de cambios

### 19 de Mayo de 2026
- **Fase 4 de refactorización completada**: DIP en casos de uso, lifespan del scheduler, CORS por env.
- **Endpoint `/auth/me`** añadido para diagnóstico de sesión JWT en producción.
- **`require_admin`** mejorado: usa `has_role()` con fallback + logging detallado.
- **`create_deal`**: corregido para no pasar NULL en campos con `server_default` (`exclude_none=True`).
- **ADR-002** creado: documenta la decisión de migrar a API Gateway.

### 15 de Mayo de 2026
- **Migración de Esquema**: Recreación de las 12 tablas base del esquema v2.0.
- **Galería Multimedia**: Extracción de múltiples imágenes desde Amazon en la API.
- **Gestión de Roles**: Recuperación del acceso admin tras reset de BD.
- **Optimización de UI**: Columnas `short_description` e `images` sincronizadas con el nuevo esquema.
- **Fase 3 completada**: Panel de admin (crear/editar/borrar chollos y categorías) migrado a FastAPI.

---

## 🚀 Recuperar datos tras un reseteo de BD

1. Ejecutar el script SQL de creación de tablas y tipos enumerados.
2. Insertar categorías y tiendas con los scripts de población.
3. Asignar el rol `admin` al usuario principal:
   ```sql
   INSERT INTO user_roles (user_id, role) VALUES ('<tu-user-id>', 'admin');
   ```
4. Verificar con `GET /auth/me` en el backend que `is_admin: true`.
