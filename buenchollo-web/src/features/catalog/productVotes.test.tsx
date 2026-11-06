import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { TopProduct } from "@/services/api/catalog";
import { ProductVoteButton } from "./ProductVoteButton";
import { TopProducts } from "./TopProducts";
import { resetProductVotes } from "./productVotes";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  top: vi.fn(),
  vote: vi.fn(),
  myVotes: vi.fn(),
  toast: { success: vi.fn(), error: vi.fn() },
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
vi.mock("@/services/api/catalog", () => ({
  catalogService: { top: mocks.top, vote: mocks.vote, myVotes: mocks.myVotes },
}));
vi.mock("sonner", () => ({ toast: mocks.toast }));

const product: TopProduct = {
  id: "p-1",
  title: "Monitor 4K",
  image_url: null,
  deal_slug: "monitor-4k",
  deal_status: "active",
  current_price: 199,
  vote_count: 2,
  position: 1,
};

describe("estado compartido de votos a producto", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    resetProductVotes();
    mocks.useAuth.mockReturnValue({ user: { id: "u-1" } });
    mocks.myVotes.mockResolvedValue([]);
    mocks.vote.mockResolvedValue({ voted: true });
    mocks.top.mockResolvedValue([{ ...product, vote_count: 3 }]);
  });

  it("agrupa en una sola petición el estado de todas las tarjetas visibles", async () => {
    mocks.myVotes.mockResolvedValue(["p-2"]);
    render(
      <>
        <ProductVoteButton productId="p-1" />
        <ProductVoteButton productId="p-2" />
        <ProductVoteButton productId="p-2" />
      </>,
    );
    await waitFor(() =>
      expect(
        screen.getAllByRole("button", { name: "Retirar voto a este producto del top" }),
      ).toHaveLength(2),
    );
    expect(mocks.myVotes).toHaveBeenCalledTimes(1);
    expect(mocks.myVotes).toHaveBeenCalledWith(["p-1", "p-2"]);
  });

  it("un voto desde la tarjeta actualiza el top sin volver a pedir el estado", async () => {
    render(
      <>
        <TopProducts slug="monitores" initialProducts={[product]} />
        <ProductVoteButton productId="p-1" />
      </>,
    );
    await waitFor(() => expect(mocks.myVotes).toHaveBeenCalledTimes(1));

    await userEvent.click(screen.getByRole("button", { name: "Votar este producto para el top" }));

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Retirar voto a Monitor 4K" })).toHaveTextContent(
        "3",
      ),
    );
    expect(mocks.top).toHaveBeenCalledWith("monitores");
    expect(mocks.myVotes).toHaveBeenCalledTimes(1);
    expect(mocks.toast.success).toHaveBeenCalledWith("Producto votado para el top");
  });

  it("si falla el voto avisa y conserva el estado anterior", async () => {
    mocks.vote.mockRejectedValue(new Error("caída"));
    render(<ProductVoteButton productId="p-1" />);
    await waitFor(() => expect(mocks.myVotes).toHaveBeenCalled());

    await userEvent.click(screen.getByRole("button", { name: "Votar este producto para el top" }));

    await waitFor(() => expect(mocks.toast.error).toHaveBeenCalled());
    expect(screen.getByRole("button", { name: "Votar este producto para el top" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("al cambiar de usuario descarta los votos del anterior", async () => {
    mocks.myVotes.mockResolvedValueOnce(["p-1"]).mockResolvedValueOnce([]);
    const { rerender } = render(<ProductVoteButton productId="p-1" />);
    await screen.findByRole("button", { name: "Retirar voto a este producto del top" });

    mocks.useAuth.mockReturnValue({ user: { id: "u-2" } });
    await act(async () => rerender(<ProductVoteButton productId="p-1" />));

    await waitFor(() => expect(mocks.myVotes).toHaveBeenCalledTimes(2));
    expect(screen.getByRole("button", { name: "Votar este producto para el top" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });
});
