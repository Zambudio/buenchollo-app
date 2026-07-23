/** Flujo público del blog: listado (datos vía React Query en el cliente,
 * mockeable con page.route) y detalle (cargado en un loader SSR — igual que
 * `chollo.$slug.tsx`, se ejecuta en el proceso del servidor de Vite y por
 * tanto no es interceptable por `page.route`; aquí solo comprobamos que la
 * página no rompe y degrada correctamente cuando el artículo no existe).
 *
 * El renderizado del bloque de producto y sus atributos `rel` ya están
 * cubiertos a nivel de componente en
 * `src/features/blog/components/public/ProductRecommendationCard.test.tsx`. */
import { expect, test } from "@playwright/test";

const CARD = {
  id: "p1",
  title: "Guía de auriculares 2026",
  slug: "guia-auriculares-2026",
  excerpt: "Comparativa de los mejores auriculares del año.",
  cover_image_url: "https://placehold.co/600x400",
  cover_image_alt: "Auriculares",
  tags: [],
  is_featured: false,
  published_at: "2026-07-01T10:00:00Z",
  reading_time_minutes: 5,
  category: {
    id: "c1",
    name: "Auriculares",
    slug: "auriculares",
    description: null,
    is_active: true,
    sort_order: 0,
  },
};

test.describe("Blog público", () => {
  test("el listado muestra los artículos publicados", async ({ page }) => {
    await page.route("**/v1/blog/posts**", (route) =>
      route.fulfill({ json: { items: [CARD], page: 1, page_size: 12, total: 1, total_pages: 1 } }),
    );
    await page.route("**/v1/blog/categories", (route) => route.fulfill({ json: [CARD.category] }));

    await page.goto("/blog");
    await expect(page.getByText("Guía de auriculares 2026").first()).toBeVisible({
      timeout: 10_000,
    });
  });

  test("un artículo inexistente muestra un estado no-encontrado sin romper la página", async ({
    page,
  }) => {
    await page.goto("/blog/articulo-que-no-existe");
    await expect(page.getByRole("heading", { name: /no encontrado/i })).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole("link", { name: /volver al blog/i })).toBeVisible();
  });
});
