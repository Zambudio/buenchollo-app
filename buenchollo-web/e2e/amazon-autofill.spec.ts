import { readFileSync } from "node:fs";

import { expect, test } from "@playwright/test";

const supabaseUrl = /^VITE_SUPABASE_URL=(.+)$/m
  .exec(readFileSync(".env", "utf8"))?.[1]
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

test("envía link.amazon al autocompletado del backend", async ({ page }) => {
  test.setTimeout(90_000);
  const shortUrl = "https://link.amazon/B01eQCJsW";
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });

  await page.route("**/v1/**", (route) => {
    const url = new URL(route.request().url());
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
    if (url.pathname.endsWith("/products/preview-from-url")) {
      return route.fulfill({
        json: {
          title: "Producto desde link.amazon",
          brand: "Marca",
          asin: "B0H7X5D6QN",
          product_url: "https://www.amazon.es/dp/B0H7X5D6QN",
          affiliate_url: shortUrl,
          image_url: "",
          current_price: 99,
          original_price: 129,
          discount_percentage: 23,
          store: "Amazon",
          category: "",
          category_id: null,
          subcategory_id: null,
          description: "Descripción",
          short_description: "Descripción corta",
          long_description: "Descripción larga",
          telegram_text: "Texto Telegram",
          images: [],
          expires_at: null,
        },
      });
    }
    if (url.pathname.endsWith("/scheduled-deals/admin/next-slot")) {
      return route.fulfill({ json: { scheduled_at: "2026-09-27T10:00:00Z" } });
    }
    if (url.pathname.endsWith("/telegram/channels")) return route.fulfill({ json: [] });
    if (url.pathname.endsWith("/telegram/categories")) {
      return route.fulfill({ json: { categories: [] } });
    }
    if (url.pathname.endsWith("/telegram/generate")) {
      return route.fulfill({ json: { text: "Texto Telegram", suggested_categories: [] } });
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

  const previewRequest = page.waitForRequest((request) =>
    request.url().includes("/products/preview-from-url"),
  );
  await page.getByPlaceholder("https://www.amazon.es/dp/...").fill(shortUrl);
  await page.getByRole("button", { name: "AUTOCOMPLETAR" }).click();
  const request = await previewRequest;

  expect(request.postDataJSON()).toMatchObject({ url: shortUrl });
  await expect(page.getByText("Datos importados desde tu NAS")).toBeVisible();
  expect(consoleErrors).toEqual([]);
});
