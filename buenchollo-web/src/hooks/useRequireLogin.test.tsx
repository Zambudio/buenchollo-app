import { renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useRequireLogin } from "@/hooks/useRequireLogin";

const mocks = vi.hoisted(() => ({ nav: vi.fn(), useAuth: vi.fn() }));

vi.mock("@tanstack/react-router", () => ({ useNavigate: () => mocks.nav }));
vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));

beforeEach(() => {
  vi.clearAllMocks();
  window.history.replaceState(null, "", "/favoritos");
});

describe("useRequireLogin", () => {
  it("sin sesión redirige a login conservando la página actual", () => {
    mocks.useAuth.mockReturnValue({ user: null, loading: false });
    renderHook(() => useRequireLogin());
    expect(mocks.nav).toHaveBeenCalledWith({
      to: "/login",
      search: { redirect: "/favoritos" },
      replace: true,
    });
  });

  it("mientras carga la sesión no redirige", () => {
    mocks.useAuth.mockReturnValue({ user: null, loading: true });
    renderHook(() => useRequireLogin());
    expect(mocks.nav).not.toHaveBeenCalled();
  });

  it("con sesión no redirige", () => {
    mocks.useAuth.mockReturnValue({ user: { id: "u1" }, loading: false });
    renderHook(() => useRequireLogin());
    expect(mocks.nav).not.toHaveBeenCalled();
  });
});
