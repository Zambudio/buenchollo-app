import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { DealTelegramDraftSection } from "./DealTelegramDraftSection";

const mocks = vi.hoisted(() => ({
  generate: vi.fn(),
  listPublications: vi.fn(),
}));

// Solo se simulan las llamadas HTTP; los métodos derivados (latestPublication) usan los mocks.
vi.mock("@/services/api/telegram", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/services/api/telegram")>();
  return { ...actual, telegramApi: { ...actual.telegramApi, ...mocks } };
});

const request = {
  title: "DJI Osmo Pocket 3",
  current_price: 269,
  previous_price: 429,
  copy_context: "Sensor CMOS de 1 pulgada",
};

beforeEach(() => {
  vi.clearAllMocks();
  mocks.listPublications.mockResolvedValue([]);
});

function renderSection(onChange = vi.fn(), value = "") {
  renderWithProviders(
    <DealTelegramDraftSection
      dealId="d1"
      value={value}
      onChange={onChange}
      buildRequest={() => request}
      provider="openai"
      onProviderChange={vi.fn()}
    />,
  );
  return onChange;
}

describe("DealTelegramDraftSection", () => {
  it("genera con IA usando el motor elegido y añade los hashtags sugeridos", async () => {
    const user = userEvent.setup();
    mocks.generate.mockResolvedValue({
      text: "🍄 DJI Osmo Pocket 3\n\n✏️Gimbal de bolsillo\n\n",
      suggested_categories: ["#Camara"],
      ai_copy: "Gimbal de bolsillo",
    });
    const onChange = renderSection();

    await user.click(screen.getByRole("button", { name: /generar publicación/i }));

    await waitFor(() =>
      expect(onChange).toHaveBeenCalledWith(
        "🍄 DJI Osmo Pocket 3\n\n✏️Gimbal de bolsillo\n\n#Camara",
      ),
    );
    expect(mocks.generate).toHaveBeenCalledWith({ ...request, ai_copy: true, provider: "openai" });
  });

  it("muestra el último envío y permite reutilizarlo con el precio actual", async () => {
    const user = userEvent.setup();
    mocks.listPublications.mockResolvedValue([
      {
        id: "p1",
        deal_id: "d1",
        channel_kind: "main",
        source: "panel",
        text: "Precio: 299,00 €",
        image_url: null,
        price: 299,
        previous_price: 429,
        discount_percentage: 30,
        sent_at: "2026-11-10T10:00:00Z",
        repriced_text: "Precio: 269,00 €",
      },
    ]);
    const onChange = renderSection();

    await user.click(await screen.findByText(/último envío/i));
    await user.click(screen.getByRole("button", { name: /usar este texto con el precio actual/i }));

    expect(onChange).toHaveBeenCalledWith("Precio: 269,00 €");
  });

  it("sin envíos lo indica", async () => {
    renderSection();
    expect(await screen.findByText(/sin envíos registrados/i)).toBeInTheDocument();
  });
});
