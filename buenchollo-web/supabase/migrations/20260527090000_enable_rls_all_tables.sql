-- =============================================
-- Hardening de seguridad — RLS en todas las tablas de public
-- =============================================
-- Contexto (2026-05-27): Supabase reportó "rls_disabled_in_public" como
-- vulnerabilidad crítica. Aunque el frontend ya cumple ADR-002 (todo el
-- acceso a datos pasa por FastAPI), el `anon key` es público y permitía
-- acceso directo a las tablas sin RLS.
--
-- Esta migración activa RLS en las 12 tablas de `public`. Las políticas
-- existentes (definidas en migraciones anteriores: 'Comments public read',
-- 'Stores public read', 'Users manage own ...', etc.) siguen vigentes.
-- El backend usa la `service_role key` que bypassa RLS por diseño, así que
-- la API sigue operando con normalidad.
--
-- Idempotente: ENABLE ROW LEVEL SECURITY no falla si ya estaba activado.

ALTER TABLE public.alerts          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.categories      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.comment_votes   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deal_comments   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deal_votes      ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deals           ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.favorites       ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_logs     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles        ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stores          ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_roles      ENABLE ROW LEVEL SECURITY;
