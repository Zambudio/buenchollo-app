-- `user_roles` tiene RLS activada desde 20260527090000_enable_rls_all_tables.sql
-- pero en algún momento se quedó sin ninguna política (posiblemente al
-- retirar `public.has_role`, que ya no existe). Con RLS activa y cero
-- políticas, CUALQUIER lectura desde el rol `authenticated` devuelve vacío
-- -- incluida la que hacen las políticas de Storage (blog-images,
-- deal-images) para comprobar "¿el usuario es admin?" antes de dejar subir
-- una imagen, que por tanto siempre fallaban con
-- "new row violates row-level security policy" aunque el usuario SÍ fuera
-- admin. El backend no lo sufre porque usa la conexión de servicio, que
-- bypassa RLS.
--
-- Política mínima: cada usuario autenticado puede ver su propia fila (para
-- que su propio uid resuelva en los checks de "soy admin" de Storage).
-- No se reintroduce una política de gestión general de roles (eso vive en
-- el backend, `require_admin`).
DROP POLICY IF EXISTS "Users view own role" ON public.user_roles;
CREATE POLICY "Users view own role" ON public.user_roles
  FOR SELECT USING (auth.uid() = user_id);
