import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { ApiError } from "@/services/api/client";
import type { Category } from "@/services/api/categories";
import type { DealDetailData } from "@/services/api/deals";
import type { Store } from "@/services/api/stores";
import type { AdminSubmission } from "@/services/api/submissions";
import { SubmissionReviewPanel } from "./SubmissionReviewPanel";

const mocks = vi.hoisted(() => ({
  approve: vi.fn(),
  reject: vi.fn(),
  navigate: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mocks.navigate,
  Link: ({
    children,
    to,
    params,
  }: {
    children: React.ReactNode;
    to: string;
    params?: { slug: string };
  }) => <a href={params ? to.replace("$slug", params.slug) : to}>{children}</a>,
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => ({ user: { id: "admin-1" } }) }));
vi.mock("sonner", () => ({ toast: { success: mocks.toastSuccess, error: mocks.toastError } }));
vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  adminSubmissionsApi: { approve: mocks.approve, reject: mocks.reject },
}));

const cats = [{ id: "cat-1", name: "Monitores", slug: "monitores", parent_id: null }] as Category[];
const subcats = [{ id: "sub-1", name: "Gaming", slug: "gaming", parent_id: "cat-1" }] as Category[];
const stores = [{ id: "store-amazon", name: "Amazon" }] as Store[];

function submission(over: Partial<AdminSubmission> = {}): AdminSubmission {
  return {
    id: "s-1",
    status: "pending",
    title: "Monitor 27 pulgadas",
    description: "Panel IPS",
    original_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=otro-21",
    affiliate_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21",
    current_price: 149.9,
    previous_price: 199,
    coupon_code: "MONI10",
    shipping_info: "Gratis",
    store_id: "store-amazon",
    store_name: "Amazon",
    category_id: "cat-1",
    subcategory_id: "sub-1",
    starts_at: null,
    expires_at: null,
    image_url: "https://img.test/a.webp",
    images: ["https://img.test/a.webp"],
    warnings: ["third_party_affiliate_removed"],
    rejection_reason: null,
    deal_slug: null,
    created_at: new Date().toISOString(),
    author: { username: "pepe", display_name: "Pepe", avatar_url: null },
    previously_published: true,
    ...over,
  };
}

const deal = { id: "d-1", slug: "monitor-27", title: "Monitor 27 pulgadas" } as DealDetailData;

function renderPanel(over: Partial<AdminSubmission> = {}) {
  const onApproved = vi.fn();
  const onRejected = vi.fn();
  const onClose = vi.fn();
  renderWithProviders(
    <SubmissionReviewPanel
      submission={submission(over)}
      stores={stores}
      cats={cats}
      subcats={subcats}
      onApproved={onApproved}
      onRejected={onRejected}
      onClose={onClose}
    />,
  );
  return { onApproved, onRejected, onClose };
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.approve.mockResolvedValue(deal);
  mocks.reject.mockResolvedValue(submission({ status: "rejected" }));
});

describe("SubmissionReviewPanel", () => {
  it("muestra enlaces original y reescrito como externos, avisos y autor", () => {
    renderPanel();
    const original = screen.getByRole("link", { name: /tag=otro-21/ });
    const rewritten = screen.getByRole("link", { name: /tag=buenchollo-21/ });
    for (const link of [original, rewritten]) {
      expect(link).toHaveAttribute("target", "_blank");
      expect(link).toHaveAttribute("rel", "noopener noreferrer nofollow");
    }
    const warnings = screen.getByRole("list", { name: "Avisos" });
    expect(within(warnings).getByText("Afiliado ajeno eliminado")).toBeInTheDocument();
    expect(
      within(warnings).getByText("Se borrará el chollo caducado anterior al aprobar"),
    ).toBeInTheDocument();
    expect(screen.getByText("Pepe")).toBeInTheDocument();
  });

  it("precarga el formulario con los datos de la propuesta", () => {
    renderPanel();
    expect(screen.getByPlaceholderText("Título *")).toHaveValue("Monitor 27 pulgadas");
    expect(screen.getByPlaceholderText("Código de descuento (opcional)")).toHaveValue("MONI10");
    expect(screen.getByPlaceholderText("Enlace afiliado *")).toHaveValue(
      "https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21",
    );
    expect(screen.getByPlaceholderText(/ASIN de Amazon/)).toHaveValue("B0ABCDEF12");
    expect(screen.queryByRole("button", { name: /Publicar en Telegram/ })).not.toBeInTheDocument();
  });

  it("aprobar llama a approve con el payload del formulario", async () => {
    const user = userEvent.setup();
    const { onApproved } = renderPanel();
    await user.clear(screen.getByPlaceholderText("Título *"));
    await user.type(screen.getByPlaceholderText("Título *"), "Monitor editado");
    await user.click(screen.getByRole("button", { name: "Aprobar y publicar" }));

    await waitFor(() => expect(mocks.approve).toHaveBeenCalledTimes(1));
    const [id, payload] = mocks.approve.mock.calls[0] ?? [];
    expect(id).toBe("s-1");
    expect(payload).toMatchObject({
      title: "Monitor editado",
      current_price: 149.9,
      previous_price: 199,
      discount_percentage: 25,
      coupon_code: "MONI10",
      shipping_info: "Gratis",
      affiliate_url: "https://www.amazon.es/dp/B0ABCDEF12?tag=buenchollo-21",
      store_id: "store-amazon",
      category_id: "cat-1",
      subcategory_id: "sub-1",
      external_id: "B0ABCDEF12",
      status: "active",
      image_url: "https://img.test/a.webp",
      images: ["https://img.test/a.webp"],
      scheduled_for: null,
    });
    expect(payload.slug).toMatch(/^monitor-editado-/);
    await waitFor(() => expect(onApproved).toHaveBeenCalledWith(deal, false));
  });

  it("con Telegram marcado lo comunica al aprobar", async () => {
    const user = userEvent.setup();
    const { onApproved } = renderPanel();
    const checkbox = screen.getByRole("checkbox", { name: "Publicar también en Telegram" });
    expect(checkbox).not.toBeChecked();
    await user.click(checkbox);
    await user.click(screen.getByRole("button", { name: "Aprobar y publicar" }));
    await waitFor(() => expect(onApproved).toHaveBeenCalledWith(deal, true));
  });

  it("propuesta programada envía status scheduled y scheduled_for", async () => {
    const user = userEvent.setup();
    const startsAt = new Date(Date.now() + 3 * 24 * 3600_000);
    startsAt.setSeconds(0, 0);
    renderPanel({ starts_at: startsAt.toISOString() });
    await user.click(screen.getByRole("button", { name: "Aprobar y publicar" }));
    await waitFor(() => expect(mocks.approve).toHaveBeenCalled());
    const payload = mocks.approve.mock.calls[0]?.[1];
    expect(payload.status).toBe("scheduled");
    expect(payload.scheduled_for).toBe(startsAt.toISOString());
    expect(payload.published_at).toBeUndefined();
  });

  it("409 DUPLICATE_DEAL avisa con enlace al chollo existente", async () => {
    const user = userEvent.setup();
    mocks.approve.mockRejectedValue(
      new ApiError(409, "dup", {
        code: "DUPLICATE_DEAL",
        detail: "dup",
        existing_deal: { id: "d-0", slug: "monitor-viejo", title: "Monitor viejo" },
      }),
    );
    const { onApproved } = renderPanel();
    await user.click(screen.getByRole("button", { name: "Aprobar y publicar" }));
    await waitFor(() => expect(mocks.toastError).toHaveBeenCalled());
    const [message, options] = mocks.toastError.mock.calls[0] ?? [];
    expect(message).toMatch(/Ya hay un chollo activo/);
    options.action.onClick();
    expect(mocks.navigate).toHaveBeenCalledWith({
      to: "/chollo/$slug",
      params: { slug: "monitor-viejo" },
    });
    expect(onApproved).not.toHaveBeenCalled();
  });

  it("otros errores muestran el detalle del backend", async () => {
    const user = userEvent.setup();
    mocks.approve.mockRejectedValue(new ApiError(409, "La propuesta ya no está pendiente", null));
    renderPanel();
    await user.click(screen.getByRole("button", { name: "Aprobar y publicar" }));
    await waitFor(() =>
      expect(mocks.toastError).toHaveBeenCalledWith("La propuesta ya no está pendiente"),
    );
  });

  it("rechazar exige motivo", async () => {
    const user = userEvent.setup();
    renderPanel();
    await user.click(screen.getByRole("button", { name: "Rechazar" }));
    const dialog = await screen.findByRole("dialog", { name: "Rechazar propuesta" });
    await user.click(within(dialog).getByRole("button", { name: "Rechazar propuesta" }));
    expect(await within(dialog).findByRole("alert")).toHaveTextContent(/mínimo 3 caracteres/);
    expect(mocks.reject).not.toHaveBeenCalled();
  });

  it("rechazar envía motivo predefinido + texto libre", async () => {
    const user = userEvent.setup();
    const { onRejected } = renderPanel();
    await user.click(screen.getByRole("button", { name: "Rechazar" }));
    const dialog = await screen.findByRole("dialog", { name: "Rechazar propuesta" });
    await user.click(within(dialog).getByRole("radio", { name: "Precio no es una oferta" }));
    await user.type(within(dialog).getByRole("textbox"), "Estaba más barato ayer");
    await user.click(within(dialog).getByRole("button", { name: "Rechazar propuesta" }));
    await waitFor(() =>
      expect(mocks.reject).toHaveBeenCalledWith(
        "s-1",
        "Precio no es una oferta: Estaba más barato ayer",
      ),
    );
    await waitFor(() => expect(onRejected).toHaveBeenCalled());
    expect(mocks.toastSuccess).toHaveBeenCalledWith("Propuesta rechazada");
  });

  it("rechazar solo con texto libre", async () => {
    const user = userEvent.setup();
    renderPanel();
    await user.click(screen.getByRole("button", { name: "Rechazar" }));
    const dialog = await screen.findByRole("dialog", { name: "Rechazar propuesta" });
    await user.type(within(dialog).getByRole("textbox"), "Producto no disponible en España");
    await user.click(within(dialog).getByRole("button", { name: "Rechazar propuesta" }));
    await waitFor(() =>
      expect(mocks.reject).toHaveBeenCalledWith("s-1", "Producto no disponible en España"),
    );
  });

  it("propuestas no pendientes no muestran acciones", () => {
    renderPanel({ status: "rejected", rejection_reason: "Ya publicado" });
    expect(screen.queryByRole("button", { name: "Aprobar y publicar" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Rechazar" })).not.toBeInTheDocument();
    expect(screen.getByText("Motivo del rechazo: Ya publicado")).toBeInTheDocument();
  });
});
