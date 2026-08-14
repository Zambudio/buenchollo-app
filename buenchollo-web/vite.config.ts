import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, loadEnv } from "vite";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { cloudflare } from "@cloudflare/vite-plugin";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Configuración nativa del stack (Vite + TanStack Start + Cloudflare Worker).
// El alias "@/*" se resuelve desde tsconfig.json vía vite-tsconfig-paths.
// Las variables VITE_* las inyecta Vite automáticamente en import.meta.env.
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiProxyTarget = env.LOCAL_API_PROXY_TARGET;

  return {
    server: {
      host: "::",
      port: 8080,
      proxy: apiProxyTarget
        ? {
            "/nas-api": {
              target: apiProxyTarget,
              changeOrigin: true,
              secure: true,
              rewrite: (path) => path.replace(/^\/nas-api/, ""),
            },
          }
        : undefined,
    },
    resolve: {
      // Alias explícito de respaldo: en unidades de red con doble letra de unidad
      // (N: / Z: apuntando al mismo NAS), vite-tsconfig-paths no siempre resuelve "@/*".
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
      dedupe: [
        "react",
        "react-dom",
        "react/jsx-runtime",
        "react/jsx-dev-runtime",
        "@tanstack/react-query",
        "@tanstack/query-core",
      ],
    },
    plugins: [
      tailwindcss(),
      tsConfigPaths({ projects: ["./tsconfig.json"] }),
      // Adaptador de Cloudflare Workers: solo en build (entorno SSR).
      ...(command === "build" ? [cloudflare({ viteEnvironment: { name: "ssr" } })] : []),
      tanstackStart(),
      viteReact(),
    ],
  };
});
