
-- 1) STORES: ocultar columnas de afiliado al público.
-- Mantenemos SELECT en la tabla pero revocamos el acceso a las columnas sensibles
-- para los roles anon/authenticated. Los admins acceden vía service_role / policies.
REVOKE SELECT (affiliate_url_template, affiliate_id) ON public.stores FROM anon, authenticated;

-- 2) DEAL_VOTES: no exponer públicamente quién vota qué.
-- Sustituimos la policy pública por una que solo permite al usuario leer sus propios votos.
-- Los conteos agregados ya están materializados en deals.votes_up / votes_down / temperature.
DROP POLICY IF EXISTS "Votes public read" ON public.deal_votes;
CREATE POLICY "Users read own votes"
  ON public.deal_votes
  FOR SELECT
  TO authenticated
  USING (auth.uid() = user_id);

-- 3) USER_ROLES: blindar contra escalada de privilegios.
-- Revocamos INSERT/UPDATE/DELETE a roles públicos; solo el trigger SECURITY DEFINER
-- (handle_new_user) y los admins (vía policy) pueden modificar la tabla.
REVOKE INSERT, UPDATE, DELETE ON public.user_roles FROM anon, authenticated;
