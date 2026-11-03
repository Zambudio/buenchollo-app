import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MySubmissionsList } from "./MySubmissionsList";
import { renderWithProviders } from "@/test/utils";
import type { Submission } from "@/services/api/submissions";

const mocks = vi.hoisted(() => ({
  mine: vi.fn(),
  withdraw: vi.fn(),
  toastSuccess: vi.fn(),
  toastError: vi.fn(),
  useAuth: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    params,
    ...rest
  }: {
    children: React.ReactNode;
    to: string;
    params?: { slug: string };
  } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={params ? to.replace("$slug", params.slug) : to} {...rest}>
      {children}
    </a>
  ),
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));
vi.mock("sonner", () => ({ toast: { success: mocks.toastSuccess, error: mocks.toastError } }));
vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  submissionsApi: { mine: mocks.mine, withdraw: mocks.withdraw },
}));

function sub(over: Partial<Submission>): Submission {
  return {
    id: "s1",
    status: "pending",
    title: "Portátil gaming",
    description: null,
    original_url: "https://x.es/p",
    affiliate_url: "https://x.es/p",
    current_price: 499.9,
    previous_price: null,
    coupon_code: null,
    shipping_info: null,
    store_id: null,
    store_name: null,
    category_id: null,
    subcategory_id: null,
    starts_at: null,
    expires_at: null,
    image_url: "https://img.test/a.webp",
    images: [],
    warnings: [],
    rejection_reason: null,
    deal_slug: null,
    created_at: new Date().toISOString(),
    ...over,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.useAuth.mockReturnValue({ user: { id: "u" }, me: null, loading: false });
});

describe("MySubmissionsList", () => {
  it("renderiza cada estado", async () => {
    mocks.mine.mockResolvedValue([
      sub({ id: "1", title: "Uno", status: "pending" }),
      sub({ id: "2", title: "Dos", status: "approved", deal_slug: "dos-slug" }),
      sub({ id: "3", title: "Tres", status: "rejected", rejection_reason: "Precio no válido" }),
      sub({ id: "4", title: "Cuatro", status: "withdrawn" }),
    ]);
    renderWithProviders(<MySubmissionsList />);

    expect(await screen.findByText("En revisión")).toBeInTheDocument();
    expect(screen.getByText("Publicado")).toBeInTheDocument();
    expect(screen.getByText("Rechazado")).toBeInTheDocument();
    expect(screen.getByText("Retirado")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Dos/ })).toHaveAttribute("href", "/chollo/dos-slug");
    expect(screen.getByText(/Precio no válido/)).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Retirar" })).toHaveLength(1);
  });

  it("retira tras confirmar en el AlertDialog e invalida la lista", async () => {
    const user = userEvent.setup();
    mocks.mine.mockResolvedValue([sub({ id: "abc" })]);
    mocks.withdraw.mockResolvedValue(undefined);
    renderWithProviders(<MySubmissionsList />);

    await user.click(await screen.findByRole("button", { name: "Retirar" }));
    const dialog = await screen.findByRole("alertdialog");
    expect(mocks.withdraw).not.toHaveBeenCalled();
    await user.click(within(dialog).getByRole("button", { name: "Retirar chollo" }));

    await waitFor(() => expect(mocks.withdraw).toHaveBeenCalledWith("abc"));
    await waitFor(() => expect(mocks.toastSuccess).toHaveBeenCalled());
    await waitFor(() => expect(mocks.mine).toHaveBeenCalledTimes(2));
  });

  it("cancelar no retira", async () => {
    const user = userEvent.setup();
    mocks.mine.mockResolvedValue([sub({ id: "abc" })]);
    renderWithProviders(<MySubmissionsList />);

    await user.click(await screen.findByRole("button", { name: "Retirar" }));
    const dialog = await screen.findByRole("alertdialog");
    await user.click(within(dialog).getByRole("button", { name: "Cancelar" }));
    expect(mocks.withdraw).not.toHaveBeenCalled();
  });

  it("muestra error si falla al retirar", async () => {
    const user = userEvent.setup();
    mocks.mine.mockResolvedValue([sub({ id: "abc" })]);
    mocks.withdraw.mockRejectedValue(new Error("boom"));
    renderWithProviders(<MySubmissionsList />);

    await user.click(await screen.findByRole("button", { name: "Retirar" }));
    await user.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Retirar chollo",
      }),
    );
    await waitFor(() => expect(mocks.toastError).toHaveBeenCalled());
  });

  it("estado vacío con CTA de publicar", async () => {
    mocks.mine.mockResolvedValue([]);
    renderWithProviders(<MySubmissionsList />);

    expect(await screen.findByText(/todavía no has publicado/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /publicar chollo/i })).toHaveAttribute(
      "href",
      "/publicar",
    );
  });
});
