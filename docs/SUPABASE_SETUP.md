# 🗄️ Configuración de Infraestructura de Datos: Supabase

**Fecha:** 14 de mayo de 2026
**Objetivo:** Migración de la base de datos de un entorno gestionado (Lovable) a un entorno propio bajo control del desarrollador para el Proyecto de Fin de Máster.

## 1. Creación del Proyecto
- **Plataforma:** Supabase (PostgreSQL as a Service).
- **Nombre del Proyecto:** `BuenChollo`.
- **Región:** Europe (Frankfurt).
- **ID de Proyecto:** `ltekgqeqgzvrkfhsmxvy`.

## 2. Implementación del Esquema (Schema)
Se han ejecutado scripts SQL para replicar la estructura necesaria para el funcionamiento de la web:
- **Tablas Creadas:** `deals`, `profiles`, `user_roles`, `stores`, `categories`.
- **Tipos Custom (Enums):** `app_role`, `deal_status`, `deal_source`.
- **Triggers de Automatización:**
    - `on_auth_user_created`: Crea automáticamente un perfil de usuario y asigna el rol de **Administrador** al primer usuario registrado para facilitar la gestión inicial.

## 3. Integración con el Frontend (buenchollo-web)
- Se han actualizado las variables de entorno en el archivo `.env`:
    - `VITE_SUPABASE_URL`: Apuntando al nuevo endpoint.
    - `VITE_SUPABASE_PUBLISHABLE_KEY`: Nueva clave anon pública.
- Se ha verificado la conectividad mediante el servidor de desarrollo Vite (puerto 8080).

## 4. Ajustes de Seguridad y UX en Desarrollo
- **Email Confirmation:** Se ha desactivado temporalmente la confirmación por email en `Authentication > Auth Settings` para permitir un flujo de registro y pruebas más ágil durante la fase de desarrollo local.

## 5. Próximos Pasos
- Configuración de OAuth con **Google Cloud Console** para habilitar el Social Login.
- Implementación de políticas RLS (Row Level Security) para proteger los datos antes del despliegue final.

---
*Documentación técnica - Máster en Desarrollo con IA*
