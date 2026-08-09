import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { RecommendedAlertsBlock } from "./RecommendedAlertsBlock";
import { renderWithProviders } from "@/test/utils";
import type { DealDetailData } from "@/services/api/deals";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  mockNavigate: vi.fn(),
  alertsList: vi.fn(),
  alertsCreate: vi.fn(),
  alertsDelete: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mocks.mockNavigate,
  Link: ({
    children,
    to,
    ...rest
  }: { children: React.ReactNode; to: string } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
}));

vi.mock("@/hooks/useAuth", () => ({
  useAuth: mocks.useAuth,
}));

vi.mock("@/services/api/alerts", () => ({
  alertsApi: {
    list: () => mocks.alertsList(),
    create: (data: unknown) => mocks.alertsCreate(data),
    delete: (id: string) => mocks.alertsDelete(id),
  },
}));

const mockDeal: DealDetailData = {
  id: "deal-123",
  title: "Cámara instantánea Polaroid Go Generation 2 compacta",
  slug: "camara-instantanea-polaroid-go",
  image_url: "https://example.com/img.jpg",
  current_price: 79.99,
  previous_price: 99.99,
  discount_percentage: 20,
  temperature: 45,
  published_at: "2026-08-08T12:00:00Z",
  description: "Una cámara instantánea genial",
  short_description: "Polaroid Go",
  affiliate_url: "https://amazon.es/dp/123",
  status: "active",
  expires_at: null,
  shipping_info: "Envío gratis",
  comment_count: 0,
  favorite_count: 0,
  votes_up: 5,
  votes_down: 0,
  click_count: 10,
  brand: "Polaroid",
  category: { name: "Fotografía", slug: "fotografia" },
  store: { id: "store-1", name: "Amazon", slug: "amazon" },
};

describe("RecommendedAlertsBlock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useAuth.mockReturnValue({ user: { id: "user-1" }, loading: false });
    mocks.alertsList.mockResolvedValue([]);
    mocks.alertsCreate.mockResolvedValue({ id: "new-alert" });
    mocks.alertsDelete.mockResolvedValue(undefined);
  });

  it("renderiza el encabezado del bloque de alertas recomendadas", async () => {
    renderWithProviders(<RecommendedAlertsBlock deal={mockDeal} />);

    expect(
      screen.getByRole("heading", { name: /¡no te pierdas ningún chollo así!/i }),
    ).toBeInTheDocument();
    expect(screen.getByText(/te avisamos en cuanto se publique uno parecido/i)).toBeInTheDocument();
  });

  it("genera las tarjetas contextuales apropiadas para el chollo", async () => {
    renderWithProviders(<RecommendedAlertsBlock deal={mockDeal} />);

    expect(screen.getByText("Cámara instantánea")).toBeInTheDocument();
    expect(screen.getByText("Cámara")).toBeInTheDocument();
    expect(screen.getByText("Polaroid")).toBeInTheDocument();
    expect(screen.getByText("Amazon")).toBeInTheDocument();
    expect(screen.getByText("Fotografía")).toBeInTheDocument();
    expect(screen.getByText("Otra alerta")).toBeInTheDocument();
  });

  it("permite activar una alerta al hacer click", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RecommendedAlertsBlock deal={mockDeal} />);

    const buttons = screen.getAllByRole("button", { name: /activar alerta/i });
    expect(buttons[0]).toBeDefined();
    await user.click(buttons[0]!);

    expect(mocks.alertsCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        name: expect.stringContaining("Alerta:"),
      }),
    );
  });

  it("muestra 'Alerta activa' si el usuario ya tiene la alerta creada", async () => {
    mocks.alertsList.mockResolvedValue([
      {
        id: "alert-polaroid",
        name: "Alerta: Polaroid",
        keyword: null,
        brand: "Polaroid",
        category_id: null,
        store_id: null,
        is_active: true,
        created_at: "2026-08-01T00:00:00Z",
        category: null,
        store: null,
      },
    ]);

    renderWithProviders(<RecommendedAlertsBlock deal={mockDeal} />);

    expect(await screen.findByText(/alerta activa/i)).toBeInTheDocument();
  });

  it("redirige a login si un usuario anónimo intenta activar una alerta", async () => {
    mocks.useAuth.mockReturnValue({ user: null, loading: false });
    const user = userEvent.setup();

    renderWithProviders(<RecommendedAlertsBlock deal={mockDeal} />);

    const buttons = screen.getAllByRole("button", { name: /activar alerta/i });
    expect(buttons[0]).toBeDefined();
    await user.click(buttons[0]!);

    expect(mocks.mockNavigate).toHaveBeenCalledWith({ to: "/login" });
    expect(mocks.alertsCreate).not.toHaveBeenCalled();
  });

  it("al pulsar 'Personalizar' navega a /alertas/nueva con keyword sugerido", async () => {
    const user = userEvent.setup();
    renderWithProviders(<RecommendedAlertsBlock deal={mockDeal} />);

    const customBtn = screen.getByRole("button", { name: /personalizar/i });
    await user.click(customBtn);

    expect(mocks.mockNavigate).toHaveBeenCalledWith(
      expect.objectContaining({
        to: "/alertas/nueva",
      }),
    );
  });
});
