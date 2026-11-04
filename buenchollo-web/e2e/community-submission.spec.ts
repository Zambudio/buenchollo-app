/** Flujo de "chollos de usuarios": publicar una propuesta y verla en "Mis chollos".
 *  Todo el backend (/v1/**) y Supabase estan mockeados; sin red real. */
import { expect, test, type Page } from "@playwright/test";

import {
  CATEGORY_ID,
  VIEWPORTS,
  collectPageErrors,
  fulfillCommon,
  horizontalOverflow,
  json,
  loginAndGoto,
  mockSupabaseUser,
  stubRemoteImages,
} from "./support/community";

const AMAZON_URL = "https://www.amazon.es/dp/B0TESTCHOL";
const AFFILIATE_URL = "https://www.amazon.es/dp/B0TESTCHOL?tag=buenchollo-21";
const PREFILL_IMAGE = "https://m.media-amazon.com/images/I/prefill.jpg";
const UPLOADED_PASTE = "https://cdn.test/submissions/pegada.webp";
const UPLOADED_URL = "https://cdn.test/submissions/desde-url.webp";
const TITLE = "Auriculares Test Pro";
const EDITED_TITLE = "Auriculares Test Pro editados";

const prefillResult = {
  status: "ok",
  canonical_url: AMAZON_URL,
  affiliate_url: AFFILIATE_URL,
  asin: "B0TESTCHOL",
  store_id: null,
  store_name: "Amazon",
  is_amazon: true,
  previously_published: false,
  existing_deal: null,
  prefill: {
    title: TITLE,
    brand: "Test",
    description: "Descripción importada",
    current_price: 49.9,
    previous_price: 79.99,
    image_url: PREFILL_IMAGE,
    images: [PREFILL_IMAGE],
    expires_at: null,
  },
  warnings: [],
};

interface Calls {
  checkLink: unknown[];
  create: Record<string, unknown>[];
  imageUploads: { contentType: string; size: number; hasFile: boolean }[];
  fromUrl: unknown[];
}

interface Scenario {
  checkLinkResponse?: object;
  createResponse?: { status: number; body: object };
}

async function setup(page: Page, scenario: Scenario = {}) {
  const calls: Calls = { checkLink: [], create: [], imageUploads: [], fromUrl: [] };
  let submitted: object | null = null;

  await page.route("**/v1/**", (route) => {
    const request = route.request();
    if (fulfillCommon(route, { isAdmin: false })) return;
    const { pathname } = new URL(request.url());
    const method = request.method();

    if (pathname.endsWith("/submissions/check-link")) {
      calls.checkLink.push(request.postDataJSON());
      return json(route, scenario.checkLinkResponse ?? prefillResult);
    }
    if (pathname.endsWith("/submissions/images/from-url")) {
      calls.fromUrl.push(request.postDataJSON());
      return json(route, { url: UPLOADED_URL, width: 800, height: 600 });
    }
    if (pathname.endsWith("/submissions/images")) {
      const buffer = request.postDataBuffer();
      calls.imageUploads.push({
        contentType: request.headers()["content-type"] ?? "",
        size: buffer?.length ?? 0,
        hasFile: buffer?.toString("latin1").includes('name="file"') ?? false,
      });
      return json(route, { url: UPLOADED_PASTE, width: 1, height: 1 });
    }
    if (pathname.endsWith("/submissions/mine")) {
      return json(route, submitted ? [submitted] : []);
    }
    if (pathname.endsWith("/submissions") && method === "POST") {
      const body = request.postDataJSON() as Record<string, unknown>;
      calls.create.push(body);
      if (scenario.createResponse) {
        return json(route, scenario.createResponse.body, scenario.createResponse.status);
      }
      submitted = {
        id: "70000000-0000-4000-8000-000000000001",
        status: "pending",
        title: body.title,
        description: body.description ?? null,
        original_url: body.url,
        affiliate_url: AFFILIATE_URL,
        current_price: body.current_price,
        previous_price: body.previous_price ?? null,
        coupon_code: null,
        shipping_info: null,
        store_id: null,
        store_name: "Amazon",
        category_id: body.category_id,
        subcategory_id: null,
        starts_at: null,
        expires_at: null,
        image_url: body.image_url ?? null,
        images: body.images,
        warnings: [],
        rejection_reason: null,
        deal_slug: null,
        created_at: new Date().toISOString(),
      };
      return json(route, submitted, 201);
    }
    return json(route, []);
  });
  await stubRemoteImages(page);
  await mockSupabaseUser(page, "user@example.com");
  return calls;
}

/** Simula Ctrl+V de una imagen: ClipboardEvent con un DataTransfer que lleva un PNG real. */
async function pasteImageFromClipboard(page: Page) {
  await page.evaluate(async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 8;
    canvas.height = 8;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.fillStyle = "#06b6d4";
      ctx.fillRect(0, 0, 8, 8);
    }
    const blob = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("toBlob"))), "image/png"),
    );
    const data = new DataTransfer();
    data.items.add(new File([blob], "captura.png", { type: "image/png" }));
    (document.activeElement as HTMLElement | null)?.blur();
    document.dispatchEvent(
      new ClipboardEvent("paste", { clipboardData: data, bubbles: true, cancelable: true }),
    );
  });
}

for (const { name, viewport } of VIEWPORTS) {
  test.describe(`Publicar chollo · ${name}`, () => {
    test.use({ viewport });
    test.describe.configure({ timeout: 120_000 });

    test("anónimo pulsa Publicar chollo y ve el diálogo de cuenta", async ({ page }) => {
      const pageErrors = collectPageErrors(page);
      await setup(page);
      await page.goto("/");
      const dialog = page.getByRole("dialog", { name: "Comparte un chollo" });
      const publish = page
        .getByRole("button", { name: "Publicar chollo" })
        .and(page.locator(":visible"))
        .first();
      // El primer clic puede llegar antes de la hidratación de React en el dev server en frío.
      await expect(async () => {
        if (!(await dialog.isVisible())) await publish.click({ timeout: 3_000 });
        await expect(dialog).toBeVisible({ timeout: 3_000 });
      }).toPass({ timeout: 30_000 });
      await expect(
        dialog.getByText("Para compartir chollos con la comunidad necesitas una cuenta."),
      ).toBeVisible();
      await expect(dialog.getByRole("link", { name: "Crear cuenta" })).toBeVisible();
      await expect(dialog.getByRole("link", { name: "Iniciar sesión" })).toBeVisible();
      expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
      expect(pageErrors).toEqual([]);
    });

    test("pega enlace, completa el formulario con imágenes y lo ve En revisión", async ({
      page,
    }) => {
      const pageErrors = collectPageErrors(page);
      const calls = await setup(page);
      await loginAndGoto(page, "/publicar");

      await page.getByLabel("Enlace del chollo").fill(AMAZON_URL);
      await page.getByRole("button", { name: "Comprobar" }).click();

      const form = page.getByRole("form", { name: "Datos del chollo" });
      await expect(form).toBeVisible();
      expect(calls.checkLink).toEqual([{ url: AMAZON_URL }]);
      await expect(form.getByLabel("Título")).toHaveValue(TITLE);
      await expect(form.getByRole("textbox", { name: /^Precio \(€\)/ })).toHaveValue("49,90");
      const list = form.getByRole("list", { name: "Imágenes añadidas" });
      await expect(list.getByTestId("image-item")).toHaveCount(1);

      await form.getByLabel("Título").fill(EDITED_TITLE);
      await form.getByRole("combobox", { name: /^Categoría/ }).selectOption(CATEGORY_ID);

      const upload = page.waitForRequest(
        (r) => r.url().endsWith("/v1/submissions/images") && r.method() === "POST",
      );
      await pasteImageFromClipboard(page);
      await upload;
      await expect(list.getByTestId("image-item")).toHaveCount(2);
      await expect(list.locator(`[data-url="${UPLOADED_PASTE}"]`)).toBeVisible();
      expect(calls.imageUploads).toHaveLength(1);
      expect(calls.imageUploads[0].contentType).toContain("multipart/form-data");
      expect(calls.imageUploads[0].hasFile).toBe(true);
      expect(calls.imageUploads[0].size).toBeGreaterThan(50);

      await form.getByLabel("O añade una imagen por URL").fill("https://cdn.test/origen.jpg");
      await form.getByRole("button", { name: "Añadir" }).click();
      await expect(list.getByTestId("image-item")).toHaveCount(3);
      await expect(list.locator(`[data-url="${UPLOADED_URL}"]`)).toBeVisible();
      expect(calls.fromUrl).toEqual([{ url: "https://cdn.test/origen.jpg" }]);

      expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);

      await form.getByRole("button", { name: "Enviar chollo" }).click();
      await expect(page.getByRole("heading", { name: /Revisaremos tu chollo/ })).toBeVisible();

      expect(calls.create).toHaveLength(1);
      const body = calls.create[0];
      expect(body).toMatchObject({
        url: AMAZON_URL,
        title: EDITED_TITLE,
        current_price: 49.9,
        previous_price: 79.99,
        category_id: CATEGORY_ID,
      });
      expect(typeof body.current_price).toBe("number");
      expect(body.images).toEqual([PREFILL_IMAGE, UPLOADED_PASTE, UPLOADED_URL]);
      expect(body.image_url).toBe(PREFILL_IMAGE);

      await page.getByRole("link", { name: "Ver mis chollos" }).click();
      await expect(page).toHaveURL(/\/mis-chollos/);
      await expect(page.getByText("En revisión")).toBeVisible();
      await expect(page.getByText(EDITED_TITLE)).toBeVisible();
      expect(pageErrors).toEqual([]);
      expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
    });

    test("enlace ya publicado muestra el aviso y no abre el formulario", async ({ page }) => {
      await setup(page, {
        checkLinkResponse: {
          ...prefillResult,
          status: "published",
          prefill: null,
          existing_deal: {
            id: "80000000-0000-4000-8000-000000000001",
            slug: "auriculares-test-pro",
            title: TITLE,
            image_url: null,
            current_price: 49.9,
          },
        },
      });
      await loginAndGoto(page, "/publicar");

      await page.getByLabel("Enlace del chollo").fill(AMAZON_URL);
      await page.getByRole("button", { name: "Comprobar" }).click();

      await expect(page.getByText("Este chollo ya está publicado.")).toBeVisible();
      await expect(page.getByRole("link", { name: "Ver y votar" })).toHaveAttribute(
        "href",
        "/chollo/auriculares-test-pro",
      );
      await expect(page.getByRole("form", { name: "Datos del chollo" })).toHaveCount(0);
      expect(await horizontalOverflow(page)).toBeLessThanOrEqual(0);
    });

    test("409 al enviar vuelve al paso 1 con el aviso de duplicado", async ({ page }) => {
      const calls = await setup(page, {
        createResponse: {
          status: 409,
          body: {
            detail: "Ya existe una propuesta para este enlace",
            code: "SUBMISSION_DUPLICATE",
            reason: "in_review",
          },
        },
      });
      await loginAndGoto(page, "/publicar");

      await page.getByLabel("Enlace del chollo").fill(AMAZON_URL);
      await page.getByRole("button", { name: "Comprobar" }).click();
      const form = page.getByRole("form", { name: "Datos del chollo" });
      await form.getByRole("combobox", { name: /^Categoría/ }).selectOption(CATEGORY_ID);
      await form.getByRole("button", { name: "Enviar chollo" }).click();

      await expect(page.getByText(/ya está en revisión/)).toBeVisible();
      await expect(form).toHaveCount(0);
      expect(calls.create).toHaveLength(1);
    });
  });
}
