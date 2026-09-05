-- Restore the public deal-images bucket expected by the admin deal form and
-- Telegram image cropper. The original 2026-04 legacy migration was not
-- present in the current production Supabase project.

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'deal-images',
  'deal-images',
  true,
  5242880,
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/avif']
)
ON CONFLICT (id) DO UPDATE
SET name = EXCLUDED.name,
    public = EXCLUDED.public,
    file_size_limit = EXCLUDED.file_size_limit,
    allowed_mime_types = EXCLUDED.allowed_mime_types;

DROP POLICY IF EXISTS "Deal images public read" ON storage.objects;
CREATE POLICY "Deal images public read" ON storage.objects
  FOR SELECT
  USING (bucket_id = 'deal-images');

DROP POLICY IF EXISTS "Admins upload deal images" ON storage.objects;
CREATE POLICY "Admins upload deal images" ON storage.objects
  FOR INSERT
  TO authenticated
  WITH CHECK (
    bucket_id = 'deal-images'
    AND EXISTS (
      SELECT 1
      FROM public.user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );

DROP POLICY IF EXISTS "Admins update deal images" ON storage.objects;
CREATE POLICY "Admins update deal images" ON storage.objects
  FOR UPDATE
  TO authenticated
  USING (
    bucket_id = 'deal-images'
    AND EXISTS (
      SELECT 1
      FROM public.user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  )
  WITH CHECK (
    bucket_id = 'deal-images'
    AND EXISTS (
      SELECT 1
      FROM public.user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );

DROP POLICY IF EXISTS "Admins delete deal images" ON storage.objects;
CREATE POLICY "Admins delete deal images" ON storage.objects
  FOR DELETE
  TO authenticated
  USING (
    bucket_id = 'deal-images'
    AND EXISTS (
      SELECT 1
      FROM public.user_roles
      WHERE user_id = auth.uid() AND role = 'admin'
    )
  );
