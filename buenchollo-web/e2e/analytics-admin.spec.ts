import { readFileSync } from "node:fs";
import { join } from "node:path";

import { expect, test } from "@playwright/test";

const supabaseUrl = /^VITE_SUPABASE_URL=(.+)$/m
  .exec(readFileSync(".env", "utf8"))?.[1]
  ?.trim()
  .replace(/^['"]|['"]$/g, "");
if (!supabaseUrl) throw new Error("VITE_SUPABASE_URL no está configurado para el E2E");

const userId = "00000000-0000-4000-8000-000000000001";
const expiresAt = Math.floor(Date.now() / 1000) + 3600;
const jwtPart = (value: object) => Buffer.from(JSON.stringify(value)).toString("base64url");
const accessToken = `${jwtPart({ alg: "HS256", typ: "JWT" })}.${jwtPart({ sub: userId, exp: expiresAt, aud: "authenticated", role: "authenticated" })}.${jwtPart({ test: true })}`;

const overview = {
  days: 30,
  totals: {
    page_views: 1240,
    unique_visitors: 682,
    sessions: 751,
    blog_views: 356,
    telegram_visitors: 240,
    organic_visitors: 310,
    telegram_blog_visitors: 96,
    telegram_to_blog_rate: 40,
  },
  timeseries: [
    { date: "2026-09-24", views: 31, visitors: 19 },
    { date: "2026-09-25", views: 48, visitors: 30 },
    { date: "2026-09-26", views: 57, visitors: 36 },
  ],
  sources: [
    { source: "organic", views: 520, visitors: 310, sessions: 335, blog_views: 170 },
    { source: "telegram", views: 430, visitors: 240, sessions: 260, blog_views: 126 },
    { source: "direct", views: 210, visitors: 96, sessions: 110, blog_views: 45 },
    { source: "referral", views: 80, visitors: 36, sessions: 46, blog_views: 15 },
  ],
  top_pages: [
    { path: "/", views: 620, visitors: 420 },
    { path: "/blog", views: 260, visitors: 180 },
  ],
  top_articles: [
    {
      id: "00000000-0000-4000-8000-000000000002",
      title: "Guía de portátiles para estudiar",
      slug: "guia-portatiles-estudiar",
      view_count: 830,
      views: 180,
      visitors: 142,
    },
  ],
};

test.beforeEach(async ({ page }) => {
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
        json: {
          user_id: userId,
          display_name: "Admin",
          bio: "",
          avatar_url: null,
          username: "admin",
        },
      });
    }
    if (url.pathname.endsWith("/notifications/unread-count")) {
      return route.fulfill({ json: { count: 0 } });
    }
    if (url.pathname.endsWith("/notifications")) {
      return route.fulfill({ json: [] });
    }
    if (url.pathname.endsWith("/analytics/admin/overview")) {
      return route.fulfill({
        json: { ...overview, days: Number(url.searchParams.get("days")) },
      });
    }
    if (url.pathname.endsWith("/analytics/events")) {
      return route.fulfill({ json: { accepted: true, blog_view_count: null } });
    }
    if (url.pathname.includes("/categories") || url.pathname.includes("/stores")) {
      return route.fulfill({ json: [] });
    }
    return route.fulfill({
      json: { items: [], page: 1, page_size: 20, total: 0, total_pages: 0 },
    });
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
});

test("muestra la atribución y permite cambiar periodo y excluir el dispositivo", async ({
  page,
}) => {
  test.setTimeout(90_000);
  const consoleErrors: string[] = [];
  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  await page.goto("/");
  const authError = await page.evaluate(
    async ({ token }) => {
      const { supabase } = await import("/src/integrations/supabase/client.ts");
      const { error } = await supabase.auth.setSession({
        access_token: token,
        refresh_token: "test-refresh-token",
      });
      return error?.message ?? null;
    },
    { token: accessToken },
  );
  expect(authError).toBeNull();

  await page.goto("/admin/analitica");

  await expect(page).toHaveURL(/\/admin\/analitica$/);
  await expect(page.getByRole("heading", { name: "¿De dónde llegan y qué leen?" })).toBeVisible({
    timeout: 30_000,
  });
  const privacyNotice = page.getByRole("button", { name: "Entendido" });
  if (await privacyNotice.isVisible()) await privacyNotice.click();
  await expect(page.getByText("Telegram → blog")).toBeVisible();
  await expect(page.getByText("40%")).toBeVisible();

  await page.getByRole("combobox", { name: "Periodo de analítica" }).click();
  await page.getByRole("option", { name: "Últimos 7 días" }).click();
  await expect(page.getByRole("combobox", { name: "Periodo de analítica" })).toHaveText(/7 días/);

  const screenshotDir = process.env.BCT_QA_SCREENSHOT_DIR;
  if (screenshotDir) {
    await page.screenshot({ path: join(screenshotDir, "analitica-desktop.png") });
  }

  await page.getByRole("button", { name: "Excluir este dispositivo" }).click();
  await expect(page.getByRole("button", { name: "Dispositivo excluido" })).toBeVisible();
  await expect(page.getByText("Este dispositivo queda excluido")).toBeHidden({ timeout: 10_000 });

  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByText("Telegram → blog")).toBeVisible();
  const mainHasHorizontalOverflow = await page.evaluate(() => {
    const main = document.querySelector("main");
    return main ? main.scrollWidth > main.clientWidth + 1 : true;
  });
  expect(mainHasHorizontalOverflow).toBe(false);
  if (screenshotDir) {
    await page.screenshot({ path: join(screenshotDir, "analitica-mobile.png") });
  }
  expect(consoleErrors).toEqual([]);
});

test("/telegram etiqueta la entrada antes de llevar a la portada", async ({ page }) => {
  await page.goto("/telegram");

  await expect(page).toHaveURL(/\/?utm_source=telegram&utm_medium=social&utm_campaign=canal$/);
});
