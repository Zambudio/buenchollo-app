import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { renderWithProviders } from "@/test/utils";
import { TelegramPanel } from "./TelegramPanel";

const mocks = vi.hoisted(() => ({
  getChannels: vi.fn(),
  getCategories: vi.fn(),
  generate: vi.fn(),
  addCategory: vi.fn(),
  notify: vi.fn(),
}));

vi.mock("@/services/api/telegram", () => ({
  telegramApi: mocks,
}));

beforeEach(() => {
  mocks.getChannels.mockResolvedValue([{ id: "main", name: "Canal General" }]);
  mocks.getCategories.mockResolvedValue(["#Tecnología"]);
  mocks.generate.mockResolvedValue({
    text: "🍄 Chollo de prueba\n\n💶 Precio: 99.00 €",
    suggested_categories: [],
  });
  mocks.addCategory.mockResolvedValue(["#Tecnología"]);
  mocks.notify.mockResolvedValue({ ok: true });
});

describe("TelegramPanel", () => {
  it("usa la siguiente franja calculada como valor inicial", async () => {
    const nextSlot = new Date(Date.now() + 24 * 60 * 60_000);
    nextSlot.setMinutes(0, 0, 0);

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
        }}
        defaultScheduledAt={nextSlot.toISOString()}
        onClose={vi.fn()}
        onSchedule={vi.fn().mockResolvedValue(true)}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    expect((screen.getByLabelText(/fecha y hora programada/i) as HTMLInputElement).value).toMatch(
      /:00$/,
    );
    expect(
      new Date((screen.getByLabelText(/fecha y hora programada/i) as HTMLInputElement).value),
    ).toEqual(nextSlot);
  });

  it("permite programar y guardar el post generado", async () => {
    const user = userEvent.setup();
    const onSchedule = vi.fn().mockResolvedValue(true);
    const onClose = vi.fn();

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          image_url: "https://images.test/product.jpg",
        }}
        onClose={onClose}
        onSchedule={onSchedule}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    const scheduleInput = screen.getByLabelText(/fecha y hora programada/i);
    expect(scheduleInput).toHaveValue();
    expect((scheduleInput as HTMLInputElement).value).toMatch(/:00$/);

    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));

    await waitFor(() => expect(onSchedule).toHaveBeenCalledOnce());
    const request = onSchedule.mock.calls[0]?.[0];
    expect(request).toMatchObject({
      text: expect.stringContaining("Chollo de prueba"),
      image_url: "https://images.test/product.jpg",
      telegram_channel_id: "main",
    });
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("no permite programar después de la caducidad", async () => {
    const user = userEvent.setup();
    const onSchedule = vi.fn().mockResolvedValue(true);
    const expiresAt = new Date(Date.now() + 60 * 60_000);
    const scheduledAt = new Date(Date.now() + 2 * 60 * 60_000);
    scheduledAt.setMinutes(0, 0, 0);

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          expires_at: expiresAt.toISOString(),
        }}
        defaultScheduledAt={scheduledAt.toISOString()}
        onClose={vi.fn()}
        onSchedule={onSchedule}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));

    expect(onSchedule).not.toHaveBeenCalled();
  });
});
