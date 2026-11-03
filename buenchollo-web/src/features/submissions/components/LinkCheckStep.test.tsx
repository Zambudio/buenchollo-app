import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LinkCheckStep } from "./LinkCheckStep";
import { renderWithProviders } from "@/test/utils";
import { ApiError } from "@/services/api/client";
import type { LinkCheckResult } from "@/services/api/submissions";

const mocks = vi.hoisted(() => ({
  checkLink: vi.fn(),
  navigate: vi.fn(),
  refreshMe: vi.fn(),
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
    params?: Record<string, string>;
  } & React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
    <a href={params?.slug ? to.replace("$slug", params.slug) : to} {...rest}>
      {children}
    </a>
  ),
  useNavigate: () => mocks.navigate,
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => ({ refreshMe: mocks.refreshMe }) }));
vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  submissionsApi: { checkLink: mocks.checkLink },
}));

function result(over: Partial<LinkCheckResult> = {}): LinkCheckResult {
  return {
    status: "ok",
    canonical_url: "https://www.amazon.es/dp/B0",
    affiliate_url: "https://www.amazon.es/dp/B0?tag=x",
    asin: "B0",
    store_id: null,
    store_name: "Amazon",
    is_amazon: true,
    previously_published: false,
    existing_deal: null,
    prefill: null,
    warnings: ["interno"],
    ...over,
  };
}

async function check(url = "https://www.amazon.es/dp/B0") {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText(/enlace del chollo/i), url);
  await user.click(screen.getByRole("button", { name: "Comprobar" }));
}

beforeEach(() => {
  vi.clearAllMocks();
  mocks.refreshMe.mockResolvedValue(undefined);
});

describe("LinkCheckStep", () => {
  it("el input es url grande con inputMode url", () => {
    renderWithProviders(<LinkCheckStep onContinue={vi.fn()} />);
    const input = screen.getByLabelText(/enlace del chollo/i);
    expect(input).toHaveAttribute("type", "url");
    expect(input).toHaveAttribute("inputmode", "url");
  });

  it("precarga initialUrl", () => {
    renderWithProviders(<LinkCheckStep initialUrl="https://x.es/a" onContinue={vi.fn()} />);
    expect(screen.getByLabelText(/enlace del chollo/i)).toHaveValue("https://x.es/a");
  });

  it("ok llama onContinue con resultado y url, sin enseñar warnings", async () => {
    const r = result();
    mocks.checkLink.mockResolvedValue(r);
    const onContinue = vi.fn();
    renderWithProviders(<LinkCheckStep onContinue={onContinue} />);
    await check();
    await waitFor(() => expect(onContinue).toHaveBeenCalledWith(r, "https://www.amazon.es/dp/B0"));
    expect(screen.queryByText("interno")).not.toBeInTheDocument();
  });

  it("muestra el esqueleto mientras comprueba", async () => {
    mocks.checkLink.mockReturnValue(new Promise(() => {}));
    renderWithProviders(<LinkCheckStep onContinue={vi.fn()} />);
    await check();
    expect(await screen.findByRole("status", { name: /comprobando/i })).toBeInTheDocument();
  });

  it("published muestra mini tarjeta con enlace Ver y votar y no continua", async () => {
    mocks.checkLink.mockResolvedValue(
      result({
        status: "published",
        existing_deal: {
          id: "d1",
          slug: "mi-chollo",
          title: "Portátil guay",
          image_url: "https://img/x.webp",
          current_price: 199,
        },
      }),
    );
    const onContinue = vi.fn();
    renderWithProviders(<LinkCheckStep onContinue={onContinue} />);
    await check();
    expect(await screen.findByText("Portátil guay")).toBeInTheDocument();
    expect(screen.getByText(/199/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ver y votar" })).toHaveAttribute(
      "href",
      "/chollo/mi-chollo",
    );
    expect(onContinue).not.toHaveBeenCalled();
  });

  it("upcoming muestra su texto", async () => {
    mocks.checkLink.mockResolvedValue(result({ status: "upcoming" }));
    renderWithProviders(<LinkCheckStep onContinue={vi.fn()} />);
    await check();
    expect(await screen.findByText(/programado y se publicará/i)).toBeInTheDocument();
  });

  it("in_review muestra su texto", async () => {
    mocks.checkLink.mockResolvedValue(result({ status: "in_review" }));
    renderWithProviders(<LinkCheckStep onContinue={vi.fn()} />);
    await check();
    expect(await screen.findByText(/ya está en revisión/i)).toBeInTheDocument();
  });

  it("ok con previously_published avisa y continua solo al pulsar Continuar", async () => {
    const r = result({ previously_published: true });
    mocks.checkLink.mockResolvedValue(r);
    const onContinue = vi.fn();
    renderWithProviders(<LinkCheckStep onContinue={onContinue} />);
    await check();
    expect(await screen.findByText(/se publicó antes/i)).toBeInTheDocument();
    expect(onContinue).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Continuar" }));
    expect(onContinue).toHaveBeenCalledWith(r, "https://www.amazon.es/dp/B0");
  });

  it("400 muestra el mensaje en línea", async () => {
    mocks.checkLink.mockRejectedValue(new ApiError(400, "No se pudo leer el enlace", null));
    renderWithProviders(<LinkCheckStep onContinue={vi.fn()} />);
    await check();
    expect(await screen.findByRole("alert")).toHaveTextContent("No se pudo leer el enlace");
  });

  it("401 redirige a login con redirect que contiene la url", async () => {
    mocks.checkLink.mockRejectedValue(new ApiError(401, "no auth", null));
    renderWithProviders(<LinkCheckStep onContinue={vi.fn()} />);
    await check("https://www.amazon.es/dp/B0?a=1");
    await waitFor(() => expect(mocks.navigate).toHaveBeenCalled());
    const arg = mocks.navigate.mock.calls[0]![0];
    expect(arg.to).toBe("/login");
    expect(arg.search.redirect).toBe(
      `/publicar?url=${encodeURIComponent("https://www.amazon.es/dp/B0?a=1")}`,
    );
  });

  it("403 PROFILE_INCOMPLETE refresca me y avisa al padre", async () => {
    mocks.checkLink.mockRejectedValue(new ApiError(403, "perfil", { code: "PROFILE_INCOMPLETE" }));
    const onProfileIncomplete = vi.fn();
    renderWithProviders(
      <LinkCheckStep onContinue={vi.fn()} onProfileIncomplete={onProfileIncomplete} />,
    );
    await check();
    await waitFor(() => expect(mocks.refreshMe).toHaveBeenCalled());
    expect(onProfileIncomplete).toHaveBeenCalled();
  });
});
