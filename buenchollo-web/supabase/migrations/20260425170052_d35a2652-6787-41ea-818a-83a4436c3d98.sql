
-- 1. Add images array column to deals
ALTER TABLE public.deals ADD COLUMN IF NOT EXISTS images TEXT[] NOT NULL DEFAULT '{}';

-- 2. Create public storage bucket for deal images
INSERT INTO storage.buckets (id, name, public)
VALUES ('deal-images', 'deal-images', true)
ON CONFLICT (id) DO NOTHING;

-- 3. Storage policies
DROP POLICY IF EXISTS "Deal images public read" ON storage.objects;
CREATE POLICY "Deal images public read" ON storage.objects
  FOR SELECT USING (bucket_id = 'deal-images');

DROP POLICY IF EXISTS "Admins upload deal images" ON storage.objects;
CREATE POLICY "Admins upload deal images" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'deal-images' AND public.has_role(auth.uid(), 'admin'));

DROP POLICY IF EXISTS "Admins update deal images" ON storage.objects;
CREATE POLICY "Admins update deal images" ON storage.objects
  FOR UPDATE USING (bucket_id = 'deal-images' AND public.has_role(auth.uid(), 'admin'));

DROP POLICY IF EXISTS "Admins delete deal images" ON storage.objects;
CREATE POLICY "Admins delete deal images" ON storage.objects
  FOR DELETE USING (bucket_id = 'deal-images' AND public.has_role(auth.uid(), 'admin'));
