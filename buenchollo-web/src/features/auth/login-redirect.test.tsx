import { fireEvent, render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { User } from "@supabase/supabase-js";
import { supabase } from "@/integrations/supabase/client";

const mocks = vi.hoisted(() => ({
  replace: vi.fn(),
  push: vi.fn(),
  auth: { user: null as User | null, loading: false },
}));

vi.mock("@tanstack/react-router", () => ({
  createFileRoute: () => (options: Record<string, unknown>) => ({
    options,
    useSearch: () => ({ redirect: "/publicar" }),
  }),
  Link: ({ children }: { children: React.ReactNode }) => <a>{children}</a>,
  useRouter: () => ({ history: { replace: mocks.replace, push: mocks.push } }),
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => mocks.auth }));
vi.mock("@/services/api/auth", () => ({
  authApi: { sendWelcomeEmail: vi.fn().mockResolvedValue(undefined) },
}));
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: vi.fn() } }));

const { Route: LoginRoute } = await import("@/routes/login");
const { Route: RegisterRoute } = await import("@/routes/registro");
const LoginPage = LoginRoute.options.component as React.ComponentType;
const RegisterPage = RegisterRoute.options.component as React.ComponentType;

const fakeUser = { id: "u1", email: "a@b.es", user_metadata: {} } as unknown as User;

beforeEach(() => {
  vi.clearAllMocks();
  mocks.auth = { user: null, loading: false };
});

describe("login/registro tras autenticarse", () => {
  it("login navega una sola vez, con replace, al redirect", async () => {
    vi.mocked(supabase.auth.signInWithPassword).mockResolvedValue({
      data: {},
      error: null,
    } as never);
    const { container, rerender } = render(<LoginPage />);
    fireEvent.change(container.querySelector('input[type="email"]')!, {
      target: { value: "a@b.es" },
    });
    fireEvent.change(container.querySelector('input[type="password"]')!, {
      target: { value: "secreto1" },
    });
    fireEvent.submit(container.querySelector("form")!);
    await waitFor(() => expect(mocks.replace).toHaveBeenCalledWith("/publicar"));

    mocks.auth = { user: fakeUser, loading: false };
    rerender(<LoginPage />);
    expect(mocks.replace).toHaveBeenCalledTimes(1);
    expect(mocks.push).not.toHaveBeenCalled();
  });

  it("registro con sesión activa navega una sola vez con replace", () => {
    mocks.auth = { user: fakeUser, loading: false };
    const { rerender } = render(<RegisterPage />);
    rerender(<RegisterPage />);
    expect(mocks.replace).toHaveBeenCalledTimes(1);
    expect(mocks.replace).toHaveBeenCalledWith("/publicar");
    expect(mocks.push).not.toHaveBeenCalled();
  });
});
