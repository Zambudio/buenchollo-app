/** Un usuario no administrador no accede al editor de blog. */
import { expect, test } from "@playwright/test";

test.describe("Guard de admin en /admin/blog", () => {
  test.beforeEach(async ({ page }) => {
    await page.route("**/v1/**", (route) => route.fulfill({ json: [] }));
  });

  test("sin sesión, /admin/blog redirige a /login", async ({ page }) => {
    await page.goto("/admin/blog");
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test("sin sesión, /admin/blog/nuevo redirige a /login", async ({ page }) => {
    await page.goto("/admin/blog/nuevo");
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });
});
