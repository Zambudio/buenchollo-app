/** E2E3 — Seguridad: rutas admin redirigen sin sesión.
 *
 *  El usuario anónimo intenta entrar a `/admin` → la app le redirige a
 *  `/login`. Garantiza que el guard de autenticación funciona; un fallo
 *  aquí sería un agujero de seguridad serio.
 */
import { expect, test } from "@playwright/test";

test.describe("Guard de admin", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/v1/**", (route) => route.fulfill({ json: [] }));
  });

  test("sin sesión, /admin redirige a /login", async ({ page }) => {
    await page.goto("/admin");
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test("la página de login muestra el CTA de Google OAuth", async ({ page }) => {
    await page.goto("/login");
    // Hay un botón/enlace que menciona Google; no asumimos texto exacto.
    const googleCta = page
      .getByRole("button", { name: /google/i })
      .or(page.getByRole("link", { name: /google/i }));
    await expect(googleCta.first()).toBeVisible({ timeout: 10_000 });
  });
});
