/** E2E1 — Home pública (smoke + estructura).
 *
 *  Por qué no testamos las cards renderizadas: TanStack Start hace SSR de
 *  los datos en el servidor de Node, fuera del alcance de `page.route`.
 *  Reproducir aquí el backend completo o stubear el SSR sería más coste
 *  que valor para el alcance del TFM.
 *
 *  En su lugar verificamos que la página responde, que el chrome de la
 *  app está presente, y que los CTA principales son accesibles. La
 *  corrección del contenido dinámico se cubre con los integration tests
 *  de Vitest (DealCard.test.tsx) y manualmente vía docs/SMOKE_TEST.md.
 */
import { expect, test } from "@playwright/test";

test.describe("Home pública", () => {
  test("la página responde 200 y carga el shell", async ({ page }) => {
    const response = await page.goto("/");
    expect(response?.status()).toBe(200);
  });

  test("el header muestra el logo BuenChollo Tech", async ({ page }) => {
    await page.goto("/");
    // El logo es un Link a "/" con el texto BUENCHOLLO_TECH renderizado en
    // varios elementos. Usar getByText con regex tolerante a fragmentos.
    await expect(page.getByText(/BUENCHOLLO/i).first()).toBeVisible();
  });

  test("el header tiene un buscador identificado por su input id", async ({ page }) => {
    await page.goto("/");
    await expect(page.locator("input#header-search")).toBeVisible();
  });

  test("hay botón para abrir el drawer de categorías", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: /abrir menú de categorías/i })).toBeVisible();
  });
});
