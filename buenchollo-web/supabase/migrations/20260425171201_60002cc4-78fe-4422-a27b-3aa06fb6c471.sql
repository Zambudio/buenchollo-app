-- 1. Add scheduled_for column for scheduled publication date
ALTER TABLE public.deals ADD COLUMN IF NOT EXISTS scheduled_for TIMESTAMPTZ;

-- 2. Function to auto-update statuses based on time
CREATE OR REPLACE FUNCTION public.process_deal_statuses()
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Publicar programados cuya fecha ya llegó
  UPDATE public.deals
    SET status = 'active', published_at = COALESCE(scheduled_for, now())
    WHERE status = 'scheduled' AND scheduled_for IS NOT NULL AND scheduled_for <= now();

  -- Caducar activos cuya fecha de expiración ya pasó
  UPDATE public.deals
    SET status = 'expired'
    WHERE status = 'active' AND expires_at IS NOT NULL AND expires_at <= now();
END;
$$;

-- 3. Trigger to auto-process on insert/update of a single row (immediate effect)
CREATE OR REPLACE FUNCTION public.deal_status_autotransition()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  -- Si está programado y la fecha ya pasó → activar
  IF NEW.status = 'scheduled' AND NEW.scheduled_for IS NOT NULL AND NEW.scheduled_for <= now() THEN
    NEW.status := 'active';
    NEW.published_at := COALESCE(NEW.scheduled_for, now());
  END IF;
  -- Si está activo y ya caducó → caducar
  IF NEW.status = 'active' AND NEW.expires_at IS NOT NULL AND NEW.expires_at <= now() THEN
    NEW.status := 'expired';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS deals_status_autotransition ON public.deals;
CREATE TRIGGER deals_status_autotransition
  BEFORE INSERT OR UPDATE ON public.deals
  FOR EACH ROW EXECUTE FUNCTION public.deal_status_autotransition();

-- 4. Programar pg_cron cada minuto para procesar transiciones automáticas
CREATE EXTENSION IF NOT EXISTS pg_cron;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM cron.job WHERE jobname = 'process-deal-statuses') THEN
    PERFORM cron.unschedule('process-deal-statuses');
  END IF;
END $$;

SELECT cron.schedule(
  'process-deal-statuses',
  '* * * * *',
  $$ SELECT public.process_deal_statuses(); $$
);