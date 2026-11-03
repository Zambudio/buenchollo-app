import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({
  auth: {} as Record<string, unknown>,
  refreshMe: vi.fn(),
  navigate: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (options: Record<string, unknown>) => ({
    options,
    useSearch: () => ({ url: undefined }),
  }),
  Link: ({
    children,
    to,
    search,
    className,
  }: {
    children: React.ReactNode;
    to: string;
    search?: { redirect?: string };
    className?: string;
  }) => (
    <a
      href={search?.redirect ? `${to}?redirect=${encodeURIComponent(search.redirect)}` : to}
      className={className}
    >
      {children}
    </a>
  ),
  useNavigate: () => mocks.navigate,
}));
vi.mock("@/components/layout/Layout", () => ({
  Layout: ({ children }: { children: React.ReactNode }) => <main>{children}</main>,
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => mocks.auth }));
vi.mock("@/features/submissions/components/LinkCheckStep", () => ({
  LinkCheckStep: ({ onProfileIncomplete }: { onProfileIncomplete?: () => void }) => (
    <button type="button" onClick={onProfileIncomplete}>
      paso 1 (simular 403)
    </button>
  ),
}));

const { Route } = await import("@/routes/publicar");
const PublishPage = Route.options.component as React.ComponentType;

const user = { id: "u1" };

beforeEach(() => {
  vi.clearAllMocks();
  mocks.refreshMe.mockResolvedValue(undefined);
  mocks.auth = {
    user: null,
    me: null,
    loading: false,
    refreshMe: mocks.refreshMe,
  };
});

describe("/publicar", () => {
  it("sin sesión, tras cerrar el diálogo siguen los enlaces Crear cuenta / Iniciar sesión", async () => {
    renderWithProviders(<PublishPage />);
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    fireEvent.keyDown(document.activeElement ?? document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    const register = screen.getByRole("link", { name: "Crear cuenta" });
    const login = screen.getByRole("link", { name: "Iniciar sesión" });
    expect(register).toHaveAttribute("href", "/registro?redirect=%2Fpublicar");
    expect(login).toHaveAttribute("href", "/login?redirect=%2Fpublicar");
  });

  it("el aviso de perfil incompleto se quita cuando me.needs_onboarding pasa a false", async () => {
    mocks.auth = { ...mocks.auth, user, me: { needs_onboarding: false } };
    const { rerender } = renderWithProviders(<PublishPage />);

    await userEvent.click(screen.getByRole("button", { name: /simular 403/i }));
    expect(screen.getByText("Completa tu perfil para poder compartir chollos")).toBeInTheDocument();

    mocks.auth = { ...mocks.auth, me: { needs_onboarding: true } };
    rerender(<PublishPage />);
    expect(screen.getByText("Completa tu perfil para poder compartir chollos")).toBeInTheDocument();

    mocks.auth = { ...mocks.auth, me: { needs_onboarding: false } };
    rerender(<PublishPage />);
    expect(
      screen.queryByText("Completa tu perfil para poder compartir chollos"),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /simular 403/i })).toBeInTheDocument();
  });

  it("si el refresco de me sigue diciendo que no falta nada, el aviso no se queda atascado", async () => {
    mocks.auth = { ...mocks.auth, user, me: { needs_onboarding: false } };
    const { rerender } = renderWithProviders(<PublishPage />);
    await userEvent.click(screen.getByRole("button", { name: /simular 403/i }));
    expect(screen.getByText(/completa tu perfil/i)).toBeInTheDocument();

    mocks.auth = { ...mocks.auth, me: { needs_onboarding: false } };
    rerender(<PublishPage />);
    expect(screen.queryByText(/completa tu perfil/i)).not.toBeInTheDocument();
  });

  it("Reintentar en el aviso refresca me y vuelve al paso 1", async () => {
    mocks.auth = { ...mocks.auth, user, me: { needs_onboarding: false } };
    renderWithProviders(<PublishPage />);
    await userEvent.click(screen.getByRole("button", { name: /simular 403/i }));
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: /reintentar/i }));
    });
    expect(mocks.refreshMe).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /simular 403/i })).toBeInTheDocument();
  });
});
