// FIXTURES sintéticas: la API se simula con page.route; ningún dato es real
// ni se valida aquí la integración en vivo con Awin.
import { existsSync, readFileSync } from "node:fs";

import { expect, test, type Page } from "@playwright/test";

const localEnv = existsSync(".env") ? readFileSync(".env", "utf8") : "";
const supabaseUrl =
  process.env.VITE_SUPABASE_URL ??
  /^VITE_SUPABASE_URL=(.+)$/m
    .exec(localEnv)?.[1]
    ?.trim()
    .replace(/^['"]|['"]$/g, "");
if (!supabaseUrl) throw new Error("VITE_SUPABASE_URL no está configurado para el E2E");

const userId = "00000000-0000-4000-8000-000000000001";
const jwtPart = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
const accessToken = `${jwtPart({ alg: "HS256", typ: "JWT" })}.${jwtPart({
  sub: userId,
  exp: Math.floor(Date.now() / 1000) + 3600,
  aud: "authenticated",
  role: "authenticated",
})}.${jwtPart({ test: true })}`;

const productUrl = "https://www.pccomponentes.com/fixture-monitor-27-qhd";
const program = {
  id: "prog-1",
  name: "PcComponentes",
  network: "awin",
  advertiser_id: "20982",
  membership_status: "joined",
  membership_checked_at: "2026-11-08T08:00:00Z",
  enabled: true,
  disclosure_text: "Enlace de afiliado.",
  image_channels: ["web", "telegram"],
  max_data_age_hours: 24,
  store_id: null,
};

async function setup(page: Page) {
  const calls: { path: string; body: unknown }[] = [];
  await page.route("**/v1/**", (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    if (route.request().method() === "POST") {
      calls.push({ path, body: route.request().postDataJSON() });
    }
    if (path.endsWith("/auth/me")) {
      return route.fulfill({
        json: {
          user_id: userId,
          email: "admin@example.com",
          roles: ["admin"],
          is_admin: true,
          has_profile: true,
          needs_onboarding: false,
          display_name: "Admin",
          avatar_url: null,
          username: "admin",
        },
      });
    }
    if (path.endsWith("/users/me/profile")) {
      return route.fulfill({
        json: { user_id: userId, display_name: "Admin", bio: "", avatar_url: null },
      });
    }
    if (path.endsWith("/notifications/unread-count")) return route.fulfill({ json: { count: 0 } });
    if (path.endsWith("/affiliates/import")) {
      return route.fulfill({
        json: {
          status: "imported",
          message: "Producto importado: revisa los campos pendientes antes de guardar.",
          stage: "product_imported",
          program,
          program_options: [],
          link: {
            status: "generated",
            affiliate_url:
              "https://www.awin1.com/cread.php?awinmid=20982&awinaffid=3148595&ued=fixture",
            source: "awin_linkbuilder",
          },
          offer: {
            title: "FIXTURE Monitor 27 QHD",
            short_description: "Panel IPS 27 QHD 165 Hz.",
            description: "Panel IPS 27 QHD 165 Hz.",
            current_price: "199.90",
            rrp_price: "279.00",
            reference_price: null,
            reference_type: "none",
            shipping_info: "Envío: 4,99 € (según la red)",
            image_url: null,
            affiliate_url:
              "https://www.awin1.com/cread.php?awinmid=20982&awinaffid=3148595&ued=fixture",
            store_id: null,
            external_id: "aw:20982:F-1001",
            affiliate_program_id: "prog-1",
            data_source: "awin_feed",
          },
          provenance: {
            data_source: "awin_feed",
            feed_id: "90001",
            provider_updated_at: new Date(Date.now() - 2 * 36e5).toISOString(),
            imported_at: new Date().toISOString(),
            freshness: "fresh",
            max_data_age_hours: 24,
          },
          missing: ["previous_price_evidence", "image_url", "category"],
          blockers: [],
          candidates: [],
          existing_deal: null,
          warnings: [
            "El feed trae PVP recomendado: se muestra aparte y no cuenta como precio anterior.",
          ],
        },
      });
    }
    if (path.endsWith("/affiliates/readiness")) {
      return route.fulfill({
        json: {
          applies: true,
          ready: false,
          blockers: [
            { code: "previous_price", message: "Falta un precio anterior mayor que el actual" },
            { code: "category", message: "Falta la categoría" },
            { code: "image", message: "Falta la imagen principal" },
          ],
          savings_amount: null,
          discount_percentage: null,
        },
      });
    }
    if (path.endsWith("/scheduled-deals/admin/next-slot")) {
      return route.fulfill({ json: { scheduled_at: "2026-11-09T10:00:00Z" } });
    }
    if (path.endsWith("/telegram/categories")) return route.fulfill({ json: { categories: [] } });
    return route.fulfill({ json: [] });
  });
  await page.route(`${supabaseUrl}/auth/v1/user`, (route) =>
    route.fulfill({
      json: {
        id: userId,
        aud: "authenticated",
        role: "authenticated",
        email: "admin@example.com",
        app_metadata: {},
        user_metadata: {},
        identities: [],
        created_at: "2026-01-01T00:00:00Z",
      },
    }),
  );
  await page.goto("/");
  await page.evaluate(
    async ({ token }) => {
      const { supabase } = await import("/src/integrations/supabase/client.ts");
      await supabase.auth.setSession({ access_token: token, refresh_token: "test-refresh-token" });
    },
    { token: accessToken },
  );
  return calls;
}

for (const viewport of [
  { name: "movil", width: 390, height: 844 },
  { name: "escritorio", width: 1280, height: 900 },
]) {
  test(`importa un producto Awin como borrador sin publicar (${viewport.name})`, async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    const calls = await setup(page);
    await page.goto("/admin/chollos");

    await page.getByPlaceholder("https://www.amazon.es/dp/...").fill(productUrl);
    await page.getByRole("button", { name: "AUTOCOMPLETAR" }).click();

    const panel = page.getByRole("region", { name: "Resultado de la importación" });
    await expect(panel.getByText("Producto importado", { exact: true }).first()).toBeVisible();
    await expect(panel.getByText(/PVP recomendado del feed: 279.00/)).toBeVisible();
    await expect(page.getByPlaceholder("Título *")).toHaveValue("FIXTURE Monitor 27 QHD");
    await expect(page.getByPlaceholder("Precio anterior")).toHaveValue("");
    await expect(page.getByLabel("Estado", { exact: true })).toHaveValue("draft");
    await expect(page.getByText("Solo se puede guardar como borrador:")).toBeVisible();
    await expect(page.getByRole("button", { name: /Publicar en Telegram/ })).toBeDisabled();

    // Nada se publica: ni alta de chollo ni Telegram.
    expect(
      calls.some((c) => c.path.includes("/deals/admin") || c.path.includes("/telegram/notify")),
    ).toBe(false);
    expect(calls.find((c) => c.path.endsWith("/affiliates/import"))?.body).toMatchObject({
      url: productUrl,
    });

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    if (process.env.E2E_SCREENSHOT_DIR) {
      await page.screenshot({
        path: `${process.env.E2E_SCREENSHOT_DIR}/affiliate-import-${viewport.name}.png`,
        fullPage: true,
      });
    }
  });
}

const programs = [
  {
    id: "prog-1",
    network: "awin",
    advertiser_id: "20982",
    name: "PcComponentes",
    store_id: null,
    domains: ["pccomponentes.com"],
    country: "ES",
    currency: "EUR",
    membership_status: "unknown",
    membership_checked_at: null,
    membership_source: null,
    promo_spaces: [],
    feeds: [
      {
        feed_id: "90001",
        name: "FIXTURE Feed A",
        language: "es",
        selected: false,
        available: true,
      },
    ],
    supports_import: true,
    supports_links: true,
    deeplink_verified_at: null,
    restrictions: { image_channels: [] },
    disclosure_text: "Enlace de afiliado.",
    max_data_age_hours: 24,
    enabled: false,
    notes: null,
    updated_at: null,
  },
  {
    id: "prog-2",
    network: "tradedoubler",
    advertiser_id: "270504",
    name: "MediaMarkt ES",
    store_id: null,
    domains: ["mediamarkt.es"],
    country: "ES",
    currency: "EUR",
    membership_status: "unknown",
    membership_checked_at: null,
    membership_source: null,
    promo_spaces: [],
    feeds: [],
    supports_import: true,
    supports_links: true,
    deeplink_verified_at: null,
    restrictions: { image_channels: [], notes: "Imágenes restringidas: verificar." },
    disclosure_text: null,
    max_data_age_hours: 24,
    enabled: false,
    notes: null,
    updated_at: null,
  },
];

for (const viewport of [
  { name: "movil", width: 390, height: 844 },
  { name: "escritorio", width: 1280, height: 900 },
]) {
  test(`registro de afiliación sin secretos ni desbordamiento (${viewport.name})`, async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await page.setViewportSize({ width: viewport.width, height: viewport.height });
    await setup(page);
    await page.route("**/v1/affiliates/programs", (route) => route.fulfill({ json: programs }));
    await page.route("**/v1/affiliates/status", (route) =>
      route.fulfill({
        json: {
          awin_publisher_api: false,
          awin_feeds: false,
          tradedoubler_products: false,
          tradedoubler_site_id: false,
        },
      }),
    );
    await page.goto("/admin/afiliacion");
    await expect(page.getByText("PcComponentes · awin · 20982")).toBeVisible();
    await expect(page.getByText("Deeplink verificado en mi cuenta TD")).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth,
    );
    expect(overflow).toBeLessThanOrEqual(0);
    if (process.env.E2E_SCREENSHOT_DIR) {
      await page.screenshot({
        path: `${process.env.E2E_SCREENSHOT_DIR}/affiliate-admin-${viewport.name}.png`,
        fullPage: true,
      });
    }
  });
}
