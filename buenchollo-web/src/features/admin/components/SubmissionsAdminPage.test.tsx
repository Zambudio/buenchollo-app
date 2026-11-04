import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { ApiError } from "@/services/api/client";
import type { DealDetailData } from "@/services/api/deals";
import type { AdminSubmission } from "@/services/api/submissions";
import { SubmissionsAdminPage } from "./SubmissionsAdminPage";

const mocks = vi.hoisted(() => ({
  list: vi.fn(),
  get: vi.fn(),
  approve: vi.fn(),
  reject: vi.fn(),
  navigate: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  telegramPanel: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mocks.navigate,
  Link: ({ children }: { children: React.ReactNode }) => <a href="#">{children}</a>,
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => ({ user: { id: "admin-1" } }) }));
vi.mock("sonner", () => ({ toast: { success: mocks.toastSuccess, error: mocks.toastError } }));
vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  adminSubmissionsApi: {
    list: mocks.list,
    get: mocks.get,
    approve: mocks.approve,
    reject: mocks.reject,
  },
}));
vi.mock("@/services/api/stores", () => ({
  storesService: { getAll: vi.fn().mockResolvedValue([]) },
}));
vi.mock("@/services/api/categories", () => ({
  categoriesService: { getAll: vi.fn().mockResolvedValue([]) },
}));
vi.mock("@/features/telegram/components/TelegramPanel", () => ({
  TelegramPanel: (props: { dealData: { title: string; affiliate_url: string } }) => {
    mocks.telegramPanel(props);
    return <div data-testid="telegram-panel">{props.dealData.title}</div>;
  },
}));

function submission(over: Partial<AdminSubmission> = {}): AdminSubmission {
  return {
    id: "s-1",
    status: "pending",
    title: "Monitor 27 pulgadas",
    description: null,
    original_url: "https://www.amazon.de/dp/B0ABCDEF12",
    affiliate_url: "https://www.amazon.de/dp/B0ABCDEF12",
    current_price: 149.9,
    previous_price: null,
    coupon_code: null,
    shipping_info: null,
    store_id: null,
    store_name: null,
    category_id: null,
    subcategory_id: null,
    starts_at: null,
    expires_at: null,
    image_url: "https://img.test/a.webp",
    images: ["https://img.test/a.webp"],
    warnings: ["amazon_foreign_marketplace"],
    rejection_reason: null,
    deal_slug: null,
    created_at: new Date(Date.now() - 3 * 3600_000).toISOString(),
    author: { username: "pepe", display_name: "Pepe", avatar_url: null },
    previously_published: false,
    ...over,
  };
}

const deal = {
  id: "d-1",
  slug: "monitor-27",
  title: "Monitor 27 pulgadas",
  current_price: 149.9,
  previous_price: null,
  discount_percentage: null,
  short_description: null,
  affiliate_url: "https://www.amazon.de/dp/B0ABCDEF12",
  expires_at: null,
  image_url: "https://img.test/a.webp",
  images: ["https://img.test/a.webp"],
} as unknown as DealDetailData;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.list.mockResolvedValue([submission()]);
  mocks.get.mockResolvedValue(submission());
  mocks.approve.mockResolvedValue(deal);
});

describe("SubmissionsAdminPage", () => {
  it("lista las pendientes con precio, autor, antigüedad y avisos", async () => {
    renderWithProviders(<SubmissionsAdminPage selectedId={undefined} onSelect={vi.fn()} />);
    const queue = await screen.findByRole("region", { name: "Cola de propuestas" });
    expect(await within(queue).findByRole("button", { name: "Monitor 27 pulgadas" })).toBeVisible();
    expect(within(queue).getByText("149,90 €")).toBeInTheDocument();
    expect(within(queue).getByText("Pepe")).toBeInTheDocument();
    expect(within(queue).getByText("hace 3 h")).toBeInTheDocument();
    expect(within(queue).getByText("Amazon de otro país (sin nuestro tag)")).toBeInTheDocument();
    expect(mocks.list).toHaveBeenCalledWith("pending");
  });

  it("las pestañas piden el estado correspondiente", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SubmissionsAdminPage selectedId={undefined} onSelect={vi.fn()} />);
    await user.click(screen.getByRole("tab", { name: "Rechazadas" }));
    await waitFor(() => expect(mocks.list).toHaveBeenCalledWith("rejected"));
    expect(screen.getByRole("tab", { name: "Rechazadas" })).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("seleccionar una propuesta fija el id", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithProviders(<SubmissionsAdminPage selectedId={undefined} onSelect={onSelect} />);
    await user.click(await screen.findByRole("button", { name: "Monitor 27 pulgadas" }));
    expect(onSelect).toHaveBeenCalledWith("s-1");
  });

  it("el enlace profundo abre la revisión directamente", async () => {
    renderWithProviders(<SubmissionsAdminPage selectedId="s-1" onSelect={vi.fn()} />);
    expect(await screen.findByRole("button", { name: "Aprobar y publicar" })).toBeInTheDocument();
    expect(mocks.get).toHaveBeenCalledWith("s-1");
  });

  it("id desconocido avisa y vuelve a la lista", async () => {
    mocks.get.mockRejectedValue(new ApiError(404, "No encontrada", null));
    const onSelect = vi.fn();
    renderWithProviders(<SubmissionsAdminPage selectedId="nope" onSelect={onSelect} />);
    await waitFor(() =>
      expect(mocks.toastError).toHaveBeenCalledWith("No se encontró la propuesta"),
    );
    expect(onSelect).toHaveBeenCalledWith(undefined);
  });

  it("aprobar con Telegram: toast con enlace, limpia id y abre el panel", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    renderWithProviders(<SubmissionsAdminPage selectedId="s-1" onSelect={onSelect} />);
    await user.click(await screen.findByRole("checkbox", { name: "Publicar también en Telegram" }));
    await user.click(screen.getByRole("button", { name: "Aprobar y publicar" }));

    expect(await screen.findByTestId("telegram-panel")).toHaveTextContent("Monitor 27 pulgadas");
    expect(mocks.telegramPanel).toHaveBeenLastCalledWith(
      expect.objectContaining({
        dealData: expect.objectContaining({
          affiliate_url: "https://www.amazon.de/dp/B0ABCDEF12",
          images: ["https://img.test/a.webp"],
        }),
        onSchedule: undefined,
      }),
    );
    expect(onSelect).toHaveBeenCalledWith(undefined);
    const [message, options] = mocks.toastSuccess.mock.calls[0] ?? [];
    expect(message).toBe("Propuesta aprobada y publicada");
    options.action.onClick();
    expect(mocks.navigate).toHaveBeenCalledWith({
      to: "/chollo/$slug",
      params: { slug: "monitor-27" },
    });
  });

  it("aprobar sin Telegram no abre el panel", async () => {
    const user = userEvent.setup();
    renderWithProviders(<SubmissionsAdminPage selectedId="s-1" onSelect={vi.fn()} />);
    await user.click(await screen.findByRole("button", { name: "Aprobar y publicar" }));
    await waitFor(() => expect(mocks.toastSuccess).toHaveBeenCalled());
    expect(screen.queryByTestId("telegram-panel")).not.toBeInTheDocument();
  });
});
