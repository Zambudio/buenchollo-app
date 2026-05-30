/**
 * Configuración de Playwright para los E2E de BuenCholloTech.
 *
 * Filosofía: pocos tests E2E (3) cubriendo los flujos críticos del usuario
 * anónimo. La pirámide del módulo de Calidad recomienda usar E2E sólo para
 * "garantizar que la app no está completamente rota", no para cubrir reglas
 * de negocio (eso son los unit/integration).
 *
 * Aislamiento: cada test mockea las respuestas de /v1/* con page.route.
 * No depende del backend real (que vive en el NAS), garantizando
 * determinismo y velocidad.
 */
import { defineConfig, devices } from "@playwright/test";

// El servidor de dev de Vite (configurado por @lovable.dev/vite-tanstack-config)
// usa 8080 por defecto. Si está ocupado salta al siguiente; en CI siempre
// está libre.
const PORT = 8080;

export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts/,
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI
    ? [["html", { open: "never" }], ["github"]]
    : [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: "npm run dev",
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
