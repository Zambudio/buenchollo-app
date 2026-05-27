-- Añadir campo para mostrar gráfica de histórico de precios Keepa en la publicación
ALTER TABLE public.deals
  ADD COLUMN IF NOT EXISTS show_keepa_chart BOOLEAN NOT NULL DEFAULT FALSE;
