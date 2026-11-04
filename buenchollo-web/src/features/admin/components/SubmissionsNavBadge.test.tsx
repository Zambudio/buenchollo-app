import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { SubmissionsNavBadge } from "./SubmissionsNavBadge";

const mocks = vi.hoisted(() => ({ count: vi.fn() }));

vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  adminSubmissionsApi: { count: mocks.count },
}));

beforeEach(() => vi.clearAllMocks());

describe("SubmissionsNavBadge", () => {
  it("muestra el número de pendientes con etiqueta accesible", async () => {
    mocks.count.mockResolvedValue({ pending: 3 });
    renderWithProviders(<SubmissionsNavBadge enabled />);
    const badge = await screen.findByLabelText("3 propuestas pendientes");
    expect(badge).toHaveTextContent("3");
  });

  it("singular con una pendiente", async () => {
    mocks.count.mockResolvedValue({ pending: 1 });
    renderWithProviders(<SubmissionsNavBadge enabled />);
    expect(await screen.findByLabelText("1 propuesta pendiente")).toBeInTheDocument();
  });

  it("se oculta con cero pendientes", async () => {
    mocks.count.mockResolvedValue({ pending: 0 });
    const { container } = renderWithProviders(<SubmissionsNavBadge enabled />);
    await waitFor(() => expect(mocks.count).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("no consulta si no es admin", () => {
    const { container } = renderWithProviders(<SubmissionsNavBadge enabled={false} />);
    expect(mocks.count).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });
});
