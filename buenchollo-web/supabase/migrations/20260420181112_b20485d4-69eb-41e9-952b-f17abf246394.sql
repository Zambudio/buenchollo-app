
-- =============================================
-- ENUMS
-- =============================================
CREATE TYPE public.app_role AS ENUM ('admin', 'user');
CREATE TYPE public.deal_status AS ENUM ('active', 'expired', 'scheduled', 'draft');
CREATE TYPE public.deal_source AS ENUM ('manual', 'script', 'api', 'import');
CREATE TYPE public.alert_frequency AS ENUM ('instant', 'daily', 'weekly');
CREATE TYPE public.notification_type AS ENUM ('alert_match', 'comment_reply', 'deal_expired', 'system');

-- =============================================
-- updated_at helper
-- =============================================
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER LANGUAGE plpgsql SET search_path = public AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$;

-- =============================================
-- PROFILES
-- =============================================
CREATE TABLE public.profiles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
  username TEXT UNIQUE,
  display_name TEXT,
  avatar_url TEXT,
  bio TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Profiles are viewable by everyone" ON public.profiles FOR SELECT USING (true);
CREATE POLICY "Users insert their own profile" ON public.profiles FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users update their own profile" ON public.profiles FOR UPDATE USING (auth.uid() = user_id);
CREATE TRIGGER trg_profiles_updated BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================
-- USER ROLES (separate table, security definer)
-- =============================================
CREATE TABLE public.user_roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  role app_role NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, role)
);
ALTER TABLE public.user_roles ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION public.has_role(_user_id UUID, _role app_role)
RETURNS BOOLEAN LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public AS $$
  SELECT EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = _user_id AND role = _role)
$$;

CREATE POLICY "Users view own roles" ON public.user_roles FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Admins view all roles" ON public.user_roles FOR SELECT USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins manage roles" ON public.user_roles FOR ALL USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));

-- =============================================
-- AUTO-CREATE PROFILE + USER ROLE on signup
-- =============================================
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
  INSERT INTO public.profiles (user_id, display_name, avatar_url)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'display_name', NEW.raw_user_meta_data->>'full_name', split_part(NEW.email, '@', 1)),
    NEW.raw_user_meta_data->>'avatar_url'
  );
  INSERT INTO public.user_roles (user_id, role) VALUES (NEW.id, 'user');
  RETURN NEW;
END;
$$;
CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- =============================================
-- STORES
-- =============================================
CREATE TABLE public.stores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL UNIQUE,
  slug TEXT NOT NULL UNIQUE,
  domain TEXT,
  logo_url TEXT,
  affiliate_id TEXT,
  affiliate_url_template TEXT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.stores ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Stores public read" ON public.stores FOR SELECT USING (true);
CREATE POLICY "Admins manage stores" ON public.stores FOR ALL USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));
CREATE TRIGGER trg_stores_updated BEFORE UPDATE ON public.stores FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================
-- CATEGORIES (jerárquicas con parent_id)
-- =============================================
CREATE TABLE public.categories (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  parent_id UUID REFERENCES public.categories(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  description TEXT,
  icon TEXT,
  display_order INT NOT NULL DEFAULT 0,
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Categories public read" ON public.categories FOR SELECT USING (true);
CREATE POLICY "Admins manage categories" ON public.categories FOR ALL USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));
CREATE INDEX idx_categories_parent ON public.categories(parent_id);
CREATE TRIGGER trg_categories_updated BEFORE UPDATE ON public.categories FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================
-- DEALS (chollos)
-- =============================================
CREATE TABLE public.deals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  description TEXT,
  short_description TEXT,
  image_url TEXT,
  -- precios
  current_price NUMERIC(10,2) NOT NULL,
  previous_price NUMERIC(10,2),
  savings_amount NUMERIC(10,2) GENERATED ALWAYS AS (COALESCE(previous_price - current_price, 0)) STORED,
  discount_percentage INT,
  shipping_info TEXT,
  -- afiliado
  affiliate_url TEXT NOT NULL,
  store_id UUID REFERENCES public.stores(id) ON DELETE SET NULL,
  category_id UUID REFERENCES public.categories(id) ON DELETE SET NULL,
  subcategory_id UUID REFERENCES public.categories(id) ON DELETE SET NULL,
  brand TEXT,
  -- estado
  status deal_status NOT NULL DEFAULT 'active',
  published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ,
  -- métricas
  temperature INT NOT NULL DEFAULT 0,
  votes_up INT NOT NULL DEFAULT 0,
  votes_down INT NOT NULL DEFAULT 0,
  comment_count INT NOT NULL DEFAULT 0,
  favorite_count INT NOT NULL DEFAULT 0,
  click_count INT NOT NULL DEFAULT 0,
  -- automatización futura
  source deal_source NOT NULL DEFAULT 'manual',
  source_url TEXT,
  external_id TEXT,
  duplicate_hash TEXT,
  -- autoría
  created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(source, external_id)
);
ALTER TABLE public.deals ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Deals public read" ON public.deals FOR SELECT USING (true);
CREATE POLICY "Admins manage deals" ON public.deals FOR ALL USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));

CREATE INDEX idx_deals_status ON public.deals(status);
CREATE INDEX idx_deals_category ON public.deals(category_id);
CREATE INDEX idx_deals_store ON public.deals(store_id);
CREATE INDEX idx_deals_published ON public.deals(published_at DESC);
CREATE INDEX idx_deals_temperature ON public.deals(temperature DESC);
CREATE INDEX idx_deals_dup_hash ON public.deals(duplicate_hash);
CREATE INDEX idx_deals_search ON public.deals USING gin(to_tsvector('spanish', coalesce(title,'') || ' ' || coalesce(description,'') || ' ' || coalesce(brand,'')));

CREATE TRIGGER trg_deals_updated BEFORE UPDATE ON public.deals FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================
-- DEAL VOTES
-- =============================================
CREATE TABLE public.deal_votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  vote SMALLINT NOT NULL CHECK (vote IN (-1, 1)),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(deal_id, user_id)
);
ALTER TABLE public.deal_votes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Votes public read" ON public.deal_votes FOR SELECT USING (true);
CREATE POLICY "Users manage own votes" ON public.deal_votes FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.recalc_deal_temperature()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _deal UUID;
BEGIN
  _deal := COALESCE(NEW.deal_id, OLD.deal_id);
  UPDATE public.deals SET
    votes_up = (SELECT COUNT(*) FROM public.deal_votes WHERE deal_id = _deal AND vote = 1),
    votes_down = (SELECT COUNT(*) FROM public.deal_votes WHERE deal_id = _deal AND vote = -1),
    temperature = (SELECT COALESCE(SUM(vote),0) FROM public.deal_votes WHERE deal_id = _deal)
  WHERE id = _deal;
  RETURN COALESCE(NEW, OLD);
END;
$$;
CREATE TRIGGER trg_votes_recalc AFTER INSERT OR UPDATE OR DELETE ON public.deal_votes FOR EACH ROW EXECUTE FUNCTION public.recalc_deal_temperature();

-- =============================================
-- COMMENTS
-- =============================================
CREATE TABLE public.deal_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  parent_id UUID REFERENCES public.deal_comments(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.deal_comments ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Comments public read" ON public.deal_comments FOR SELECT USING (true);
CREATE POLICY "Users create comments" ON public.deal_comments FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users edit own comments" ON public.deal_comments FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users or admins delete comments" ON public.deal_comments FOR DELETE USING (auth.uid() = user_id OR public.has_role(auth.uid(), 'admin'));

CREATE INDEX idx_comments_deal ON public.deal_comments(deal_id);
CREATE TRIGGER trg_comments_updated BEFORE UPDATE ON public.deal_comments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE OR REPLACE FUNCTION public.recalc_deal_comment_count()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _deal UUID;
BEGIN
  _deal := COALESCE(NEW.deal_id, OLD.deal_id);
  UPDATE public.deals SET comment_count = (SELECT COUNT(*) FROM public.deal_comments WHERE deal_id = _deal) WHERE id = _deal;
  RETURN COALESCE(NEW, OLD);
END;
$$;
CREATE TRIGGER trg_comments_count AFTER INSERT OR DELETE ON public.deal_comments FOR EACH ROW EXECUTE FUNCTION public.recalc_deal_comment_count();

-- =============================================
-- FAVORITES
-- =============================================
CREATE TABLE public.favorites (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  deal_id UUID NOT NULL REFERENCES public.deals(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(user_id, deal_id)
);
ALTER TABLE public.favorites ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own favorites" ON public.favorites FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users manage own favorites" ON public.favorites FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION public.recalc_deal_favorite_count()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
DECLARE _deal UUID;
BEGIN
  _deal := COALESCE(NEW.deal_id, OLD.deal_id);
  UPDATE public.deals SET favorite_count = (SELECT COUNT(*) FROM public.favorites WHERE deal_id = _deal) WHERE id = _deal;
  RETURN COALESCE(NEW, OLD);
END;
$$;
CREATE TRIGGER trg_favorites_count AFTER INSERT OR DELETE ON public.favorites FOR EACH ROW EXECUTE FUNCTION public.recalc_deal_favorite_count();

-- =============================================
-- ALERTS
-- =============================================
CREATE TABLE public.alerts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  keyword TEXT,
  category_id UUID REFERENCES public.categories(id) ON DELETE SET NULL,
  brand TEXT,
  store_id UUID REFERENCES public.stores(id) ON DELETE SET NULL,
  min_price NUMERIC(10,2),
  max_price NUMERIC(10,2),
  min_discount INT,
  is_active BOOLEAN NOT NULL DEFAULT true,
  frequency alert_frequency NOT NULL DEFAULT 'instant',
  notify_email BOOLEAN NOT NULL DEFAULT false,
  notify_in_app BOOLEAN NOT NULL DEFAULT true,
  last_triggered_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.alerts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own alerts" ON public.alerts FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users manage own alerts" ON public.alerts FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Admins view alerts" ON public.alerts FOR SELECT USING (public.has_role(auth.uid(), 'admin'));
CREATE TRIGGER trg_alerts_updated BEFORE UPDATE ON public.alerts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================
-- NOTIFICATIONS
-- =============================================
CREATE TABLE public.notifications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type notification_type NOT NULL,
  title TEXT NOT NULL,
  body TEXT,
  link_url TEXT,
  deal_id UUID REFERENCES public.deals(id) ON DELETE CASCADE,
  alert_id UUID REFERENCES public.alerts(id) ON DELETE SET NULL,
  is_read BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Users view own notifications" ON public.notifications FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "Users update own notifications" ON public.notifications FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "Users delete own notifications" ON public.notifications FOR DELETE USING (auth.uid() = user_id);
-- inserts hechos por el sistema (admin/triggers/cron) — nadie inserta por API normal
CREATE INDEX idx_notif_user_unread ON public.notifications(user_id, is_read);

-- =============================================
-- IMPORT LOGS
-- =============================================
CREATE TABLE public.import_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  source deal_source NOT NULL,
  source_name TEXT,
  total_processed INT NOT NULL DEFAULT 0,
  total_created INT NOT NULL DEFAULT 0,
  total_updated INT NOT NULL DEFAULT 0,
  total_duplicates INT NOT NULL DEFAULT 0,
  total_errors INT NOT NULL DEFAULT 0,
  notes TEXT,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ
);
ALTER TABLE public.import_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Admins view import logs" ON public.import_logs FOR SELECT USING (public.has_role(auth.uid(), 'admin'));
CREATE POLICY "Admins manage import logs" ON public.import_logs FOR ALL USING (public.has_role(auth.uid(), 'admin')) WITH CHECK (public.has_role(auth.uid(), 'admin'));
