import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MySubmissionsPage } from "./MySubmissionsPage";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({ useAuth: vi.fn(), nav: vi.fn() }));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mocks.nav,
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));
vi.mock("@/components/layout/Layout", () => ({
  Layout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("./MySubmissionsList", () => ({ MySubmissionsList: () => <div>LISTA</div> }));

beforeEach(() => vi.clearAllMocks());

describe("MySubmissionsPage", () => {
  it("mientras carga la sesión muestra placeholder y no redirige", () => {
    mocks.useAuth.mockReturnValue({ user: null, loading: true });
    renderWithProviders(<MySubmissionsPage />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText("LISTA")).not.toBeInTheDocument();
    expect(mocks.nav).not.toHaveBeenCalled();
  });

  it("anónimo tras cargar redirige a /login?redirect=/mis-chollos", () => {
    mocks.useAuth.mockReturnValue({ user: null, loading: false });
    renderWithProviders(<MySubmissionsPage />);
    expect(mocks.nav).toHaveBeenCalledWith({
      to: "/login",
      search: { redirect: "/mis-chollos" },
      replace: true,
    });
    expect(screen.queryByText("LISTA")).not.toBeInTheDocument();
  });

  it("con sesión muestra la lista", () => {
    mocks.useAuth.mockReturnValue({ user: { id: "u" }, loading: false });
    renderWithProviders(<MySubmissionsPage />);
    expect(screen.getByText("LISTA")).toBeInTheDocument();
    expect(mocks.nav).not.toHaveBeenCalled();
  });
});
