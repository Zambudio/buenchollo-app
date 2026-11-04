import { existsSync, readFileSync } from "node:fs";

import type { Page, Route } from "@playwright/test";

const localEnv = existsSync(".env") ? readFileSync(".env", "utf8") : "";
export const supabaseUrl =
  process.env.VITE_SUPABASE_URL ??
  /^VITE_SUPABASE_URL=(.+)$/m
    .exec(localEnv)?.[1]
    ?.trim()
    .replace(/^['"]|['"]$/g, "");
if (!supabaseUrl) throw new Error("VITE_SUPABASE_URL no está configurado para el E2E");

export const userId = "00000000-0000-4000-8000-000000000001";
const jwtPart = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
const accessToken = `${jwtPart({ alg: "HS256", typ: "JWT" })}.${jwtPart({
  sub: userId,
  exp: Math.floor(Date.now() / 1000) + 3600,
  aud: "authenticated",
  role: "authenticated",
})}.${jwtPart({ test: true })}`;

export const VIEWPORTS = [
  { name: "movil 375x812", viewport: { width: 375, height: 812 } },
  { name: "escritorio 1280x800", viewport: { width: 1280, height: 800 } },
] as const;

export const CATEGORY_ID = "20000000-0000-4000-8000-000000000001";
export const SUBCATEGORY_ID = "30000000-0000-4000-8000-000000000001";
export const STORE_ID = "50000000-0000-4000-8000-000000000001";
export const categories = [
  {
    id: CATEGORY_ID,
    name: "Móviles",
    slug: "moviles",
    icon: null,
    display_order: 1,
    parent_id: null,
  },
  {
    id: SUBCATEGORY_ID,
    name: "Smartphones",
    slug: "smartphones",
    icon: null,
    display_order: 1,
    parent_id: CATEGORY_ID,
  },
];
export const stores = [
  {
    id: STORE_ID,
    name: "Amazon",
    slug: "amazon",
    domain: "amazon.es",
    logo_url: null,
    affiliate_id: null,
    affiliate_url_template: null,
    is_active: true,
  },
];

const PNG_1X1 = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP4z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==",
  "base64",
);

export const json = (route: Route, body: unknown, status = 200) =>
  route.fulfill({ status, json: body });

/** Responde los endpoints comunes (sesión, notificaciones, catálogos); false si no aplica. */
export function fulfillCommon(route: Route, opts: { isAdmin: boolean }): boolean {
  const { pathname } = new URL(route.request().url());
  if (pathname.endsWith("/auth/me")) {
    void json(route, {
      user_id: userId,
      email: "user@example.com",
      roles: opts.isAdmin ? ["admin"] : [],
      is_admin: opts.isAdmin,
      has_profile: true,
      needs_onboarding: false,
      display_name: "Usuaria Test",
      avatar_url: null,
      username: "usuaria",
    });
    return true;
  }
  if (pathname.endsWith("/users/me/profile")) {
    void json(route, { user_id: userId, display_name: "Usuaria Test", bio: "", avatar_url: null });
    return true;
  }
  if (pathname.endsWith("/notifications/unread-count")) {
    void json(route, { count: 0 });
    return true;
  }
  if (pathname.endsWith("/deals/page")) {
    void json(route, { items: [], page: 1, page_size: 30, total: 0, total_pages: 1 });
    return true;
  }
  if (pathname.endsWith("/deals/my-votes")) {
    void json(route, {});
    return true;
  }
  if (/\/deals\/(latest|popular|favorites)$/.test(pathname)) {
    void json(route, []);
    return true;
  }
  if (pathname.endsWith("/v1/categories")) {
    void json(route, categories);
    return true;
  }
  if (pathname.endsWith("/v1/stores")) {
    void json(route, stores);
    return true;
  }
  return false;
}

/** Imágenes remotas (CDN de Amazon, bucket de pruebas) sin salir a la red. */
export async function stubRemoteImages(page: Page) {
  await page.route(/https:\/\/(m\.media-amazon\.com|cdn\.test)\/.*/, (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: PNG_1X1 }),
  );
}

export async function mockSupabaseUser(page: Page, email: string) {
  await page.route(`${supabaseUrl}/auth/v1/user`, (route) =>
    route.fulfill({
      json: {
        id: userId,
        aud: "authenticated",
        role: "authenticated",
        email,
        app_metadata: {},
        user_metadata: {},
        identities: [],
        created_at: "2026-01-01T00:00:00Z",
      },
    }),
  );
}

/** Inicia sesión en Supabase (mock) y navega a `path`. */
export async function loginAndGoto(page: Page, path: string) {
  await page.goto("/");
  await page.evaluate(
    async ({ token }) => {
      const { supabase } = await import("/src/integrations/supabase/client.ts");
      await supabase.auth.setSession({ access_token: token, refresh_token: "test-refresh-token" });
    },
    { token: accessToken },
  );
  await page.goto(path);
}

/** Píxeles de desbordamiento horizontal del documento (<= 0 es correcto). */
export function horizontalOverflow(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
}

/** Recoge los errores no capturados de la página; el test debe comprobar que queda vacío.
 *  Se ignora el aviso de hidratación: el SSR del servidor Node consulta la API real
 *  (fuera del alcance de page.route) y su HTML difiere del cliente mockeado; React lo
 *  recupera solo. Cualquier otro error sí cuenta. */
export function collectPageErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("pageerror", (error) => {
    if (/Hydration failed/i.test(error.message)) return;
    errors.push(error.message);
  });
  return errors;
}
