import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PublishDealButton } from "./PublishDealButton";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({ useAuth: vi.fn() }));

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    search,
    ...rest
  }: {
    children: React.ReactNode;
    to: string;
    search?: Record<string, string>;
  } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a
      href={search && Object.keys(search).length ? `${to}?${new URLSearchParams(search)}` : to}
      {...rest}
    >
      {children}
    </a>
  ),
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));

beforeEach(() => {
  mocks.useAuth.mockReturnValue({ user: null, me: null, loading: false });
});

describe("PublishDealButton", () => {
  it("sin sesión abre el diálogo con Crear cuenta e Iniciar sesión con redirect a /publicar", async () => {
    const user = userEvent.setup();
    renderWithProviders(<PublishDealButton />);

    await user.click(screen.getByRole("button", { name: "Publicar chollo" }));

    expect(
      await screen.findByText("Para compartir chollos con la comunidad necesitas una cuenta."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Crear cuenta" })).toHaveAttribute(
      "href",
      "/registro?redirect=%2Fpublicar",
    );
    expect(screen.getByRole("link", { name: "Iniciar sesión" })).toHaveAttribute(
      "href",
      "/login?redirect=%2Fpublicar",
    );
  });

  it("con sesión es un enlace a /publicar y no abre diálogo", () => {
    mocks.useAuth.mockReturnValue({ user: { id: "u-1" }, me: null, loading: false });
    renderWithProviders(<PublishDealButton />);

    expect(screen.getByRole("link", { name: "Publicar chollo" })).toHaveAttribute(
      "href",
      "/publicar",
    );
    expect(screen.queryByText(/necesitas una cuenta/)).not.toBeInTheDocument();
  });
});
