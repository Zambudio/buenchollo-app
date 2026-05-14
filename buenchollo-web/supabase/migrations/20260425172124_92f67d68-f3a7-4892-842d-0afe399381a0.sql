-- Tabla de votos en comentarios
CREATE TABLE IF NOT EXISTS public.comment_votes (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  comment_id UUID NOT NULL REFERENCES public.deal_comments(id) ON DELETE CASCADE,
  user_id UUID NOT NULL,
  vote SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (comment_id, user_id)
);

ALTER TABLE public.comment_votes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Comment votes public read" ON public.comment_votes FOR SELECT USING (true);
CREATE POLICY "Users manage own comment votes" ON public.comment_votes FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Contadores en deal_comments
ALTER TABLE public.deal_comments
  ADD COLUMN IF NOT EXISTS votes_up INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS votes_down INTEGER NOT NULL DEFAULT 0;

-- Trigger recálculo
CREATE OR REPLACE FUNCTION public.recalc_comment_votes()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE _c UUID;
BEGIN
  _c := COALESCE(NEW.comment_id, OLD.comment_id);
  UPDATE public.deal_comments SET
    votes_up = (SELECT COUNT(*) FROM public.comment_votes WHERE comment_id = _c AND vote = 1),
    votes_down = (SELECT COUNT(*) FROM public.comment_votes WHERE comment_id = _c AND vote = -1)
  WHERE id = _c;
  RETURN COALESCE(NEW, OLD);
END;
$$;

DROP TRIGGER IF EXISTS comment_votes_recalc ON public.comment_votes;
CREATE TRIGGER comment_votes_recalc
  AFTER INSERT OR UPDATE OR DELETE ON public.comment_votes
  FOR EACH ROW EXECUTE FUNCTION public.recalc_comment_votes();

-- Función de estadísticas de usuario
CREATE OR REPLACE FUNCTION public.get_user_stats(_user_id UUID)
RETURNS TABLE (
  comments_made BIGINT,
  comments_received BIGINT,
  likes_given BIGINT,
  likes_received BIGINT,
  dislikes_received BIGINT,
  deal_votes_cast BIGINT,
  favorites_count BIGINT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    (SELECT COUNT(*) FROM public.deal_comments WHERE user_id = _user_id),
    (SELECT COUNT(*) FROM public.deal_comments c
       WHERE c.parent_id IN (SELECT id FROM public.deal_comments WHERE user_id = _user_id)),
    (SELECT COUNT(*) FROM public.comment_votes WHERE user_id = _user_id AND vote = 1),
    (SELECT COUNT(*) FROM public.comment_votes v
       JOIN public.deal_comments c ON c.id = v.comment_id
       WHERE c.user_id = _user_id AND v.vote = 1),
    (SELECT COUNT(*) FROM public.comment_votes v
       JOIN public.deal_comments c ON c.id = v.comment_id
       WHERE c.user_id = _user_id AND v.vote = -1),
    (SELECT COUNT(*) FROM public.deal_votes WHERE user_id = _user_id),
    (SELECT COUNT(*) FROM public.favorites WHERE user_id = _user_id);
$$;