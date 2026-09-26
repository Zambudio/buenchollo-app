import { existsSync, readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

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

const scheduledId = "10000000-0000-4000-8000-000000000001";
const currentCategoryId = "20000000-0000-4000-8000-000000000001";
const currentSubcategoryId = "30000000-0000-4000-8000-000000000001";
const newCategoryId = "20000000-0000-4000-8000-000000000002";
const newSubcategoryId = "30000000-0000-4000-8000-000000000002";
const newStoreId = "50000000-0000-4000-8000-000000000002";
const title = "Cafetera programada editable";

test("permite cambiar categoría y subcategoría de una publicación programada", async ({ page }) => {
  test.setTimeout(90_000);
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(11, 0, 0, 0);

  let updatePayload: Record<string, unknown> | null = null;
  const scheduledDeal = {
    id: scheduledId,
    deal_id: "40000000-0000-4000-8000-000000000001",
    asin: "B0H7X5D6QN",
    title,
    description_web: "Descripción web",
    short_description: "Descripción corta",
    telegram_text: "Texto Telegram",
    telegram_channel_id: null,
    offer_price: 1199.99,
    regular_price: 1499.99,
    discount_percentage: 20,
    image_url: null,
    images: [],
    affiliate_url: "https://link.amazon/B0dy09Zws",
    store_name: "Amazon",
    store_id: "50000000-0000-4000-8000-000000000001",
    category_id: currentCategoryId,
    subcategory_id: currentSubcategoryId,
    scheduled_at: tomorrow.toISOString(),
    expires_at: null,
    status: "programado",
    cancellation_reason: null,
    show_keepa_chart: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  await page.route("**/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/auth/me")) {
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
    if (url.pathname.endsWith("/users/me/profile")) {
      return route.fulfill({
        json: { user_id: userId, display_name: "Admin", bio: "", avatar_url: null },
      });
    }
    if (url.pathname.endsWith("/notifications/unread-count")) {
      return route.fulfill({ json: { count: 0 } });
    }
    if (url.pathname.endsWith("/notifications")) return route.fulfill({ json: [] });
    if (url.pathname === "/v1/categories") {
      return route.fulfill({
        json: [
          {
            id: currentCategoryId,
            name: "Cocina",
            slug: "cocina",
            parent_id: null,
            icon: null,
            display_order: 1,
            is_active: true,
          },
          {
            id: currentSubcategoryId,
            name: "Cafeteras",
            slug: "cafeteras",
            parent_id: currentCategoryId,
            icon: null,
            display_order: 1,
            is_active: true,
          },
          {
            id: newCategoryId,
            name: "Hogar",
            slug: "hogar",
            parent_id: null,
            icon: null,
            display_order: 2,
            is_active: true,
          },
          {
            id: newSubcategoryId,
            name: "Aspiradoras",
            slug: "aspiradoras",
            parent_id: newCategoryId,
            icon: null,
            display_order: 1,
            is_active: true,
          },
        ],
      });
    }
    if (url.pathname === "/v1/stores") {
      return route.fulfill({
        json: [
          {
            id: scheduledDeal.store_id,
            name: "Amazon",
            slug: "amazon",
            domain: "amazon.es",
            logo_url: null,
            affiliate_id: null,
            affiliate_url_template: null,
            is_active: true,
          },
          {
            id: newStoreId,
            name: "PcComponentes",
            slug: "pccomponentes",
            domain: "pccomponentes.com",
            logo_url: null,
            affiliate_id: null,
            affiliate_url_template: null,
            is_active: true,
          },
        ],
      });
    }
    if (url.pathname.endsWith("/scheduled-deals/admin")) {
      return route.fulfill({ json: [scheduledDeal] });
    }
    if (
      url.pathname.endsWith(`/scheduled-deals/admin/${scheduledId}`) &&
      request.method() === "PUT"
    ) {
      updatePayload = request.postDataJSON();
      return route.fulfill({ json: { ...scheduledDeal, ...updatePayload } });
    }
    if (url.pathname.endsWith("/telegram/channels")) return route.fulfill({ json: [] });
    if (url.pathname.endsWith("/telegram/categories")) {
      return route.fulfill({ json: { categories: [] } });
    }
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
  await page.goto("/admin/chollos");
  const privacyAcknowledgement = page.getByRole("button", { name: "ENTENDIDO" });
  if (await privacyAcknowledgement.isVisible()) await privacyAcknowledgement.click();

  await page.locator(".fc-event").filter({ hasText: title }).click();
  await expect(page.getByText("Vista previa y edición")).toBeVisible();

  await expect(page.getByLabel("Categoría web", { exact: true })).toBeVisible({ timeout: 5_000 });
  await expect(page.getByLabel("Subcategoría web")).toBeVisible({ timeout: 5_000 });
  await page.getByLabel("Tienda web").selectOption(newStoreId);
  await page.getByLabel("Categoría web", { exact: true }).selectOption(newCategoryId);
  await page.getByLabel("Subcategoría web").selectOption(newSubcategoryId);
  await page.getByLabel("Resumen web").fill("Resumen web actualizado");
  await page.getByLabel("Marca web").fill("Marca actualizada");
  await page.getByLabel("Envío web").fill("Envío 24 horas");
  await page.getByLabel("Imágenes web").fill("https://example.com/updated.jpg");
  await page.getByText("Mostrar gráfica Keepa").click();
  await page.getByRole("button", { name: "GUARDAR CAMBIOS" }).click();

  await expect.poll(() => updatePayload).not.toBeNull();
  expect(updatePayload).toMatchObject({
    short_description: "Resumen web actualizado",
    images: ["https://example.com/updated.jpg"],
    store_id: newStoreId,
    store_name: "PcComponentes",
    category_id: newCategoryId,
    subcategory_id: newSubcategoryId,
    brand: "Marca actualizada",
    shipping_info: "Envío 24 horas",
    show_keepa_chart: true,
    telegram_text: "Texto Telegram",
  });
});
