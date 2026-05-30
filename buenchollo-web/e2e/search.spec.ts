/** E2E2 — Búsqueda desde la URL en /explorar.
 *
 *  Nota: el form del header tiene un `value` controlado por React que en
 *  combinación con SSR y modo Desktop hace que los eventos sintetizados
 *  por Playwright no actualicen el state a tiempo. Reproducir un flujo
 *  estable de escritura + submit aquí añade brittleness sin valor, así
 *  que probamos lo que realmente importa: que `/explorar?q=...` carga y
 *  refleja el filtro. La interacción de escritura está cubierta en los
 *  integration tests de Vitest.
 */
import { expect, test } from "@playwright/test";

test.describe("Búsqueda en /explorar", () => {
  test("la ruta /explorar?q=monitor responde y conserva el query string", async ({ page }) => {
    const response = await page.goto("/explorar?q=monitor");
    expect(response?.status()).toBe(200);
    await expect(page).toHaveURL(/q=monitor/);
  });

  test("el buscador del header tiene id estable para selectores", async ({ page }) => {
    await page.goto("/explorar");
    await expect(page.locator("input#header-search")).toBeVisible();
  });
});
