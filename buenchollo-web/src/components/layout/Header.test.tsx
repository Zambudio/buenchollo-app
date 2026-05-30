/** Integration test del Header.
 *
 *  Verifica el comportamiento user-facing:
 *  - usuario anónimo ve el CTA de ACCEDER.
 *  - usuario logueado con notificaciones sin leer ve el badge con el conteo.
 *  - usuario admin tiene acceso al "Panel admin" en el dropdown.
 *
 *  Mockeamos las fronteras (Link de TanStack Router, useAuth, hook de
 *  notificaciones, useNavigate). El Dropdown de Radix necesita interacción
 *  para abrirse, así que algunos asserts implican click previo.
 */
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Header } from "@/components/layout/Header";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  useUnreadNotifications: vi.fn(),
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
  useNavigate: () => vi.fn(),
}));

vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));

vi.mock("@/features/notifications/hooks/useNotifications", () => ({
  useUnreadNotifications: mocks.useUnreadNotifications,
}));

// CategoriesDrawer monta lógica adicional irrelevante para los asserts de
// este test → la sustituimos por un stub vacío.
vi.mock("@/components/layout/CategoriesDrawer", () => ({
  CategoriesDrawer: () => null,
}));

beforeEach(() => {
  mocks.useAuth.mockReturnValue({ user: null, isAdmin: false, signOut: vi.fn() });
  mocks.useUnreadNotifications.mockReturnValue({ data: 0 });
});

describe("Header", () => {
  it("usuario anónimo: muestra el CTA [ ACCEDER ]", () => {
    renderWithProviders(<Header />);
    expect(screen.getByRole("link", { name: /acceder/i })).toBeInTheDocument();
  });

  it("usuario logueado: no muestra ACCEDER y enseña los enlaces de usuario", () => {
    mocks.useAuth.mockReturnValue({
      user: { id: "u-1", email: "x@y.z" },
      isAdmin: false,
      signOut: vi.fn(),
    });

    renderWithProviders(<Header />);

    expect(screen.queryByRole("link", { name: /acceder/i })).not.toBeInTheDocument();
    expect(screen.getByTitle(/notificaciones/i)).toBeInTheDocument();
    expect(screen.getByTitle(/favoritos/i)).toBeInTheDocument();
  });

  it("usuario logueado con 3 notificaciones sin leer: muestra badge '3'", () => {
    mocks.useAuth.mockReturnValue({
      user: { id: "u-1" },
      isAdmin: false,
      signOut: vi.fn(),
    });
    mocks.useUnreadNotifications.mockReturnValue({ data: 3 });

    renderWithProviders(<Header />);

    // El badge está junto al icono Bell.
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("usuario logueado con más de 9 unread muestra '9+'", () => {
    mocks.useAuth.mockReturnValue({ user: { id: "u-1" }, signOut: vi.fn() });
    mocks.useUnreadNotifications.mockReturnValue({ data: 27 });

    renderWithProviders(<Header />);

    expect(screen.getByText("9+")).toBeInTheDocument();
  });

  it("usuario admin: el menú incluye 'Panel admin'", async () => {
    mocks.useAuth.mockReturnValue({
      user: { id: "u-1" },
      isAdmin: true,
      signOut: vi.fn(),
    });
    const user = userEvent.setup();

    renderWithProviders(<Header />);
    await user.click(screen.getByRole("button", { name: /perfil/i }));

    expect(await screen.findByText(/panel admin/i)).toBeInTheDocument();
  });

  it("usuario no admin: el menú NO incluye 'Panel admin'", async () => {
    mocks.useAuth.mockReturnValue({
      user: { id: "u-1" },
      isAdmin: false,
      signOut: vi.fn(),
    });
    const user = userEvent.setup();

    renderWithProviders(<Header />);
    await user.click(screen.getByRole("button", { name: /perfil/i }));

    expect(await screen.findByText(/mi perfil/i)).toBeInTheDocument();
    expect(screen.queryByText(/panel admin/i)).not.toBeInTheDocument();
  });
});
