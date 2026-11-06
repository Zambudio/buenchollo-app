import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { TopProducts } from "./TopProducts";
import type { TopProduct } from "@/services/api/catalog";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  top: vi.fn(),
  vote: vi.fn(),
  myVotes: vi.fn(),
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
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));
vi.mock("@/services/api/catalog", () => ({ catalogService: mocks }));

const product: TopProduct = {
  id: "2a4eb5e7-91c7-4b4d-8ce4-b6c366364eef",
  title: "Monitor 4K",
  image_url: null,
  deal_slug: "monitor-4k",
  deal_status: "active",
  current_price: 199,
  vote_count: 0,
  position: 1,
};

describe("TopProducts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useAuth.mockReturnValue({ user: { id: "user-1" } });
    mocks.myVotes.mockImplementation(async () =>
      mocks.vote.mock.calls.length ? [product.id] : [],
    );
    mocks.vote.mockResolvedValue({ voted: true });
    mocks.top.mockResolvedValue([{ ...product, vote_count: 1 }]);
  });

  it("registra el voto al producto y actualiza el contador", async () => {
    render(<TopProducts slug="monitores" initialProducts={[product]} />);
    await userEvent.click(screen.getByRole("button", { name: "Votar por Monitor 4K" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Retirar voto a Monitor 4K" })).toHaveTextContent(
        "1",
      ),
    );
    expect(mocks.vote).toHaveBeenCalledWith(product.id);
    expect(mocks.top).toHaveBeenCalledWith("monitores");
  });

  it("pide iniciar sesión para votar sin usuario", () => {
    mocks.useAuth.mockReturnValue({ user: null });
    render(<TopProducts slug="monitores" initialProducts={[product]} />);
    expect(screen.getByRole("link", { name: "Accede para votar por Monitor 4K" })).toHaveAttribute(
      "href",
      "/login",
    );
  });

  it("mantiene el voto guardado si falla la recarga del ranking", async () => {
    mocks.top.mockRejectedValue(new Error("sin conexión"));
    render(<TopProducts slug="monitores" initialProducts={[product]} />);
    await userEvent.click(screen.getByRole("button", { name: "Votar por Monitor 4K" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Voto guardado");
    expect(screen.getByRole("button", { name: "Retirar voto a Monitor 4K" })).toHaveTextContent(
      "1",
    );
  });
});
