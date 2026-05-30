/** Integration test del componente DealCard.
 *
 *  Estrategia: probamos lo que el USUARIO ve y hace, no detalles internos
 *  (estado del useState, ciclo del useEffect del carrusel, etc.). Para
 *  ello mockeamos sólo las fronteras del componente:
 *
 *  - @tanstack/react-router → Link como <a> plano (no levantamos router).
 *  - @/hooks/useAuth → controlamos si hay user logueado.
 *  - @/services/api/deals → favoritesApi.toggle stub.
 *  - sonner.toast → spyable.
 */
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { DealCard, type DealCardData } from "@/features/deals/components/DealCard";
import { renderWithProviders } from "@/test/utils";

// vi.hoisted: estos mocks se materializan ANTES que los vi.mock(), que a su
// vez son hoisteados por Vitest al top del módulo. Sin esto, los vi.mock()
// no pueden referenciar las variables (ReferenceError).
const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  toggle: vi.fn(),
  toast: { error: vi.fn(), success: vi.fn() },
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    params,
  }: {
    children: React.ReactNode;
    to: string;
    params?: Record<string, string>;
  }) => {
    const href = params
      ? Object.entries(params).reduce((acc, [k, v]) => acc.replace(`$${k}`, v), to)
      : to;
    return <a href={href}>{children}</a>;
  },
}));

vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));

vi.mock("@/services/api/deals", async (importActual) => {
  const actual = await importActual<typeof import("@/services/api/deals")>();
  return { ...actual, favoritesApi: { toggle: mocks.toggle } };
});

vi.mock("sonner", () => ({ toast: mocks.toast }));

beforeEach(() => {
  mocks.useAuth.mockReturnValue({ user: null, isAdmin: false });
  mocks.toggle.mockReset();
  mocks.toast.error.mockReset();
});

function buildDeal(overrides: Partial<DealCardData> = {}): DealCardData {
  return {
    id: "d-1",
    title: "Monitor 27 pulgadas 4K",
    slug: "monitor-27-pulgadas-4k",
    image_url: "https://example.test/img.png",
    images: null,
    current_price: 199.99,
    previous_price: 299.99,
    discount_percentage: null,
    temperature: 120,
    published_at: "2026-05-30T11:00:00Z",
    store: { name: "Amazon", slug: "amazon" },
    category: { name: "Monitores", slug: "monitores" },
    ...overrides,
  };
}

describe("DealCard", () => {
  it("muestra el título y el precio formateado", () => {
    renderWithProviders(<DealCard deal={buildDeal()} />);

    expect(screen.getByRole("heading", { name: /monitor 27 pulgadas 4k/i })).toBeInTheDocument();
    expect(screen.getByText(/199,99/)).toBeInTheDocument();
    expect(screen.getByText(/299,99/)).toBeInTheDocument(); // precio tachado
  });

  it("muestra el descuento calculado en negativo", () => {
    renderWithProviders(<DealCard deal={buildDeal()} />);
    // (199.99/299.99) → 33% de descuento
    expect(screen.getByText(/-33%/)).toBeInTheDocument();
  });

  it("muestra el badge CADUCADO cuando el chollo está expirado", () => {
    renderWithProviders(<DealCard deal={buildDeal({ status: "expired" })} />);
    expect(screen.getByText(/caducado/i)).toBeInTheDocument();
  });

  it("muestra 'SIN_IMAGEN' cuando no hay imagen ni galería", () => {
    renderWithProviders(<DealCard deal={buildDeal({ image_url: null, images: null })} />);
    expect(screen.getByText(/sin_imagen/i)).toBeInTheDocument();
  });

  it("el enlace apunta a la ruta de detalle del chollo", () => {
    renderWithProviders(<DealCard deal={buildDeal()} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/chollo/monitor-27-pulgadas-4k");
  });

  it("click en favorito sin usuario logueado muestra toast de error", async () => {
    const user = userEvent.setup();
    renderWithProviders(<DealCard deal={buildDeal()} />);

    await user.click(screen.getByRole("button", { name: /guardar/i }));

    expect(mocks.toast.error).toHaveBeenCalledWith("Inicia sesión para guardar favoritos");
    expect(mocks.toggle).not.toHaveBeenCalled();
  });

  it("click en favorito con usuario logueado llama a la API", async () => {
    mocks.useAuth.mockReturnValue({ user: { id: "u-1" }, isAdmin: false });
    mocks.toggle.mockResolvedValue({ is_favorited: true });
    const user = userEvent.setup();

    renderWithProviders(<DealCard deal={buildDeal()} />);
    await user.click(screen.getByRole("button", { name: /guardar/i }));

    expect(mocks.toggle).toHaveBeenCalledWith("d-1");
    expect(mocks.toast.error).not.toHaveBeenCalled();
  });
});
