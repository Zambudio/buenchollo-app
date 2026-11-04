import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { SubmissionForm } from "./SubmissionForm";
import { renderWithProviders } from "@/test/utils";
import { ApiError } from "@/services/api/client";
import type { LinkCheckResult } from "@/services/api/submissions";

const mocks = vi.hoisted(() => ({
  create: vi.fn(),
  uploadImage: vi.fn(),
  importImageUrl: vi.fn(),
  getAll: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    ...rest
  }: { children: React.ReactNode; to: string } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
  useNavigate: () => mocks.navigate,
}));
vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  submissionsApi: {
    create: mocks.create,
    uploadImage: mocks.uploadImage,
    importImageUrl: mocks.importImageUrl,
  },
}));
vi.mock("@/services/api/categories", () => ({
  categoriesService: { getAll: mocks.getAll },
}));

const IMG_A = "https://m.media-amazon.com/images/I/a.jpg";
const IMG_B = "https://m.media-amazon.com/images/I/b.jpg";
const URL_ = "https://www.amazon.es/dp/B0TEST";

function amazonResult(over: Partial<LinkCheckResult> = {}): LinkCheckResult {
  return {
    status: "ok",
    canonical_url: URL_,
    affiliate_url: `${URL_}?tag=x`,
    asin: "B0TEST",
    store_id: "s1",
    store_name: "Amazon",
    is_amazon: true,
    previously_published: false,
    existing_deal: null,
    prefill: {
      title: "Auriculares Sony WH-1000XM5",
      brand: "Sony",
      description: "Cancelación de ruido",
      current_price: 249.9,
      previous_price: 399,
      image_url: IMG_A,
      images: [IMG_A, IMG_B],
      expires_at: null,
    },
    warnings: [],
    ...over,
  };
}

function renderForm(result = amazonResult()) {
  const props = {
    onDuplicate: vi.fn(),
    onBack: vi.fn(),
    onPublishAnother: vi.fn(),
    onProfileIncomplete: vi.fn(),
  };
  renderWithProviders(<SubmissionForm url={URL_} result={result} {...props} />);
  return props;
}

async function chooseCategory(user = userEvent.setup()) {
  const select = screen.getByLabelText(/^categoría/i);
  await waitFor(() => expect(within(select).getByRole("option", { name: "Audio" })).toBeTruthy());
  await user.selectOptions(select, "c1");
}

beforeAll(() => {
  URL.createObjectURL = vi.fn(() => "blob:preview");
  URL.revokeObjectURL = vi.fn();
});

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getAll.mockResolvedValue([
    { id: "c1", name: "Audio", slug: "audio", icon: null, display_order: 1, parent_id: null },
    { id: "c2", name: "Informática", slug: "info", icon: null, display_order: 2, parent_id: null },
    { id: "s1", name: "Auriculares", slug: "auri", icon: null, display_order: 1, parent_id: "c1" },
    { id: "s2", name: "Portátiles", slug: "port", icon: null, display_order: 1, parent_id: "c2" },
  ]);
  mocks.create.mockResolvedValue({ id: "sub-1", status: "pending" });
});

describe("SubmissionForm", () => {
  it("el prefill de Amazon rellena título, precios, descuento e imágenes", async () => {
    renderForm();
    expect(screen.getByLabelText(/^título/i)).toHaveValue("Auriculares Sony WH-1000XM5");
    expect(screen.getByLabelText(/^precio \(€\)/i)).toHaveValue("249,90");
    expect(screen.getByLabelText(/^precio anterior/i)).toHaveValue("399");
    expect(screen.getByLabelText(/^descripción/i)).toHaveValue("Cancelación de ruido");
    expect(screen.getAllByText("-37%").length).toBeGreaterThan(0);
    const items = screen.getAllByTestId("image-item");
    expect(items.map((i) => i.getAttribute("data-url"))).toEqual([IMG_A, IMG_B]);
    expect(mocks.uploadImage).not.toHaveBeenCalled();
    expect(mocks.importImageUrl).not.toHaveBeenCalled();
  });

  it("precios con inputMode decimal y descuento en vivo", async () => {
    renderForm();
    const user = userEvent.setup();
    const prev = screen.getByLabelText(/^precio anterior/i);
    expect(prev).toHaveAttribute("inputmode", "decimal");
    await user.clear(prev);
    await user.type(prev, "499,80");
    expect(screen.getAllByText("-50%").length).toBeGreaterThan(0);
  });

  it("la tienda detectada es de solo lectura; si no hay, se escribe", () => {
    renderForm();
    expect(screen.getByLabelText(/^tienda/i)).toHaveAttribute("readonly");
  });

  it("sin tienda detectada el campo tienda es editable", () => {
    renderForm(amazonResult({ store_name: null, store_id: null, is_amazon: false }));
    expect(screen.getByLabelText(/^tienda/i)).not.toHaveAttribute("readonly");
  });

  it("la subcategoría se filtra por la categoría elegida", async () => {
    renderForm();
    const user = userEvent.setup();
    await chooseCategory(user);
    const sub = screen.getByLabelText(/^subcategoría/i);
    expect(within(sub).getByRole("option", { name: "Auriculares" })).toBeInTheDocument();
    expect(within(sub).queryByRole("option", { name: "Portátiles" })).not.toBeInTheDocument();
  });

  it("muestra errores de validación en línea y enfoca el primero", async () => {
    renderForm();
    const user = userEvent.setup();
    await user.clear(screen.getByLabelText(/^título/i));
    await user.click(screen.getByRole("button", { name: /enviar chollo/i }));
    expect(await screen.findByText("El título no puede estar vacío")).toBeInTheDocument();
    expect(screen.getByText("Elige una categoría")).toBeInTheDocument();
    const title = screen.getByLabelText(/^título/i);
    expect(title).toHaveAttribute("aria-invalid", "true");
    expect(title).toHaveAttribute("aria-describedby", "sub-title-error");
    expect(title).toHaveFocus();
    expect(mocks.create).not.toHaveBeenCalled();
  });

  it("envío correcto llama a create con la portada como image_url y muestra éxito", async () => {
    renderForm();
    const user = userEvent.setup();
    await user.click(screen.getAllByRole("button", { name: "Usar como portada" })[1]!);
    await chooseCategory(user);
    await user.selectOptions(screen.getByLabelText(/^subcategoría/i), "s1");
    await user.type(screen.getByLabelText(/^código de descuento/i), "SONY10");
    await user.click(screen.getByRole("button", { name: /enviar chollo/i }));

    await waitFor(() => expect(mocks.create).toHaveBeenCalledTimes(1));
    expect(mocks.create.mock.calls[0]![0]).toEqual({
      url: URL_,
      title: "Auriculares Sony WH-1000XM5",
      description: "Cancelación de ruido",
      current_price: 249.9,
      previous_price: 399,
      coupon_code: "SONY10",
      shipping_info: undefined,
      store_name: undefined,
      category_id: "c1",
      subcategory_id: "s1",
      starts_at: undefined,
      expires_at: undefined,
      images: [IMG_B, IMG_A],
      image_url: IMG_B,
    });
    expect(
      await screen.findByText("¡Gracias! Revisaremos tu chollo y te avisaremos por email."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver mis chollos" })).toHaveAttribute(
      "href",
      "/mis-chollos",
    );
    expect(screen.getByRole("button", { name: "Publicar otro" })).toBeInTheDocument();
  });

  it("409 SUBMISSION_DUPLICATE vuelve al paso 1 con el estado", async () => {
    const existing = { id: "d1", slug: "auris", title: "Auris", image_url: null, current_price: 1 };
    mocks.create.mockRejectedValue(
      new ApiError(409, "Ya publicado", {
        code: "SUBMISSION_DUPLICATE",
        reason: "published",
        existing_deal: existing,
      }),
    );
    const props = renderForm();
    const user = userEvent.setup();
    await chooseCategory(user);
    await user.click(screen.getByRole("button", { name: /enviar chollo/i }));
    await waitFor(() => expect(props.onDuplicate).toHaveBeenCalledTimes(1));
    expect(props.onDuplicate.mock.calls[0]![0]).toMatchObject({
      status: "published",
      existing_deal: existing,
    });
  });

  it("429 muestra el mensaje del backend", async () => {
    mocks.create.mockRejectedValue(
      new ApiError(429, "Tienes 5 propuestas pendientes de revisión", null),
    );
    renderForm();
    const user = userEvent.setup();
    await chooseCategory(user);
    await user.click(screen.getByRole("button", { name: /enviar chollo/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Tienes 5 propuestas pendientes de revisión",
    );
  });

  it("422 asigna los errores del backend a sus campos", async () => {
    mocks.create.mockRejectedValue(
      new ApiError(422, "x", {
        detail: [
          { loc: ["body", "coupon_code"], msg: "Código no válido" },
          { loc: ["body"], msg: "Value error, La fecha de fin debe ser futura" },
        ],
      }),
    );
    renderForm();
    const user = userEvent.setup();
    await chooseCategory(user);
    await user.click(screen.getByRole("button", { name: /enviar chollo/i }));
    expect(await screen.findByText("Código no válido")).toBeInTheDocument();
    expect(screen.getByLabelText(/^código de descuento/i)).toHaveFocus();
    expect(screen.getByRole("alert")).toHaveTextContent("La fecha de fin debe ser futura");
  });

  it("el envío está deshabilitado mientras suben imágenes", async () => {
    mocks.uploadImage.mockReturnValue(new Promise(() => {}));
    renderForm();
    const ev = new Event("paste", { bubbles: true, cancelable: true });
    Object.defineProperty(ev, "clipboardData", {
      value: {
        files: [new File(["x"], "a.png", { type: "image/png" })],
        items: [],
        types: ["Files"],
        getData: () => "",
      },
    });
    act(() => {
      document.body.dispatchEvent(ev);
    });
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /enviar chollo/i })).toBeDisabled(),
    );
    expect(screen.getByText(/espera a que terminen/i)).toBeInTheDocument();
  });

  it("Cambiar enlace vuelve al paso 1", async () => {
    const props = renderForm();
    await userEvent.click(screen.getByRole("button", { name: /cambiar enlace/i }));
    expect(props.onBack).toHaveBeenCalled();
  });
  it("Amazon sin datos leídos avisa de rellenar a mano", () => {
    renderForm(amazonResult({ prefill: null }));
    expect(screen.getByRole("status")).toHaveTextContent(
      "No hemos podido leer los datos de Amazon. Rellena el formulario a mano.",
    );
  });

  it("sin aviso de Amazon si hay prefill o si no es Amazon", () => {
    renderForm(amazonResult());
    expect(screen.queryByText(/No hemos podido leer los datos de Amazon/)).not.toBeInTheDocument();
  });

  it("tienda no Amazon sin prefill no muestra el aviso", () => {
    renderForm(amazonResult({ prefill: null, is_amazon: false }));
    expect(screen.queryByText(/No hemos podido leer los datos de Amazon/)).not.toBeInTheDocument();
  });

  it("la región viva del descuento está siempre montada y solo cambia el texto", async () => {
    renderForm(amazonResult({ prefill: null }));
    const live = document.getElementById("sub-discount")!;
    expect(live).toHaveAttribute("aria-live", "polite");
    expect(live).toHaveTextContent("");
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/^precio \(€\)/i), "50");
    await user.type(screen.getByLabelText(/^precio anterior/i), "100");
    expect(document.getElementById("sub-discount")).toBe(live);
    expect(live).toHaveTextContent("Descuento del 50%");
  });

  it("la vista previa usa la tienda escrita si no se detectó", async () => {
    renderForm(amazonResult({ store_name: null, store_id: null, is_amazon: false }));
    await userEvent.type(screen.getByLabelText(/^tienda/i), "PcComponentes");
    const preview = screen.getByRole("figure", { name: /vista previa/i });
    expect(within(preview).getAllByText("PcComponentes").length).toBeGreaterThan(0);
  });
});
