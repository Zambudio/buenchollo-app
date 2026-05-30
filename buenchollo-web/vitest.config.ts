/**
 * Vitest + Testing Library en jsdom.
 *
 * Coverage estratégico (decisión documentada en docs/QUALITY.md):
 * - Threshold sólo sobre src/lib/** (lógica pura / CORE).
 * - Sin gate global para no perseguir 100% de mentira.
 */
import { defineConfig } from "vitest/config";
import tsconfigPaths from "vite-tsconfig-paths";

export default defineConfig({
  plugins: [tsconfigPaths()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    css: false,
    include: ["src/**/*.{test,spec}.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "node_modules/",
        "dist/",
        "src/routeTree.gen.ts",
        "src/router.tsx",
        "src/integrations/supabase/types.ts",
        "src/components/ui/**",
        "src/styles.css",
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "**/*.config.*",
        "vitest.setup.ts",
        // Config sin lógica testeable (INFRASTRUCTURE en términos del módulo
        // de Calidad). Documentado en docs/QUALITY.md.
        "src/lib/query-client.ts",
      ],
      thresholds: {
        "src/lib/**": {
          lines: 90,
          functions: 90,
          branches: 80,
          statements: 90,
        },
      },
    },
  },
});
