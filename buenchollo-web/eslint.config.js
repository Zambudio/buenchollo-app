import js from "@eslint/js";
import eslintPluginPrettier from "eslint-plugin-prettier/recommended";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";

export default tseslint.config(
  // Ignorar carpetas de build y archivos generados.
  { ignores: ["dist", ".output", ".vinxi", "src/routeTree.gen.ts"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": ["warn", { allowConstantExport: true }],
      // Forzamos tipado explícito: bloquea cualquier 'any' nuevo. El
      // routeTree.gen.ts queda exento por el ignores de arriba.
      "@typescript-eslint/no-explicit-any": "error",
      // Permitimos _vars (convención de "intencionadamente sin usar"). Nivel
      // 'warn' para no bloquear iteración del día a día.
      "@typescript-eslint/no-unused-vars": [
        "warn",
        {
          argsIgnorePattern: "^_",
          varsIgnorePattern: "^_",
          caughtErrorsIgnorePattern: "^_",
        },
      ],
      // Dependencias de hooks: error en lugar de warning. Detecta closures
      // obsoletas — uno de los bugs más frecuentes en React.
      "react-hooks/exhaustive-deps": "error",
    },
  },
  eslintPluginPrettier,
);
