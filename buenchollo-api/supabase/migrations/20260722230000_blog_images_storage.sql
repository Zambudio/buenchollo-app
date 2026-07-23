-- Public bucket for blog cover/content images (separate from deal-images).
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
  'blog-images',
  'blog-images',
  true,
  5242880,
  ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/avif']
)
ON CONFLICT (id) DO UPDATE
SET
  public = true,
  file_size_limit = 5242880,
  allowed_mime_types = ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/avif'];

DROP POLICY IF EXISTS "Blog images public read" ON storage.objects;
CREATE POLICY "Blog images public read" ON storage.objects
  FOR SELECT USING (bucket_id = 'blog-images');

-- `public.has_role` ya no existe en esta base (la autorización de admin vive
-- en el backend, `require_admin` en core/security.py, que consulta
-- `user_roles` directamente). Las políticas de Storage hacen la misma
-- comprobación inline en vez de depender de esa función.
DROP POLICY IF EXISTS "Admins upload blog images" ON storage.objects;
CREATE POLICY "Admins upload blog images" ON storage.objects
  FOR INSERT WITH CHECK (
    bucket_id = 'blog-images'
    AND EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

DROP POLICY IF EXISTS "Admins update blog images" ON storage.objects;
CREATE POLICY "Admins update blog images" ON storage.objects
  FOR UPDATE USING (
    bucket_id = 'blog-images'
    AND EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );

DROP POLICY IF EXISTS "Admins delete blog images" ON storage.objects;
CREATE POLICY "Admins delete blog images" ON storage.objects
  FOR DELETE USING (
    bucket_id = 'blog-images'
    AND EXISTS (SELECT 1 FROM public.user_roles WHERE user_id = auth.uid() AND role = 'admin')
  );
