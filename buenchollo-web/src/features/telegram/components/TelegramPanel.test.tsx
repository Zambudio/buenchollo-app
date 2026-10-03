import { fireEvent, screen, waitFor } from "@testing-library/react";
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
  cropAndUploadTelegramImage: vi.fn(),
  rotateAndUploadTelegramImage: vi.fn(),
}));

vi.mock("@/services/api/telegram", () => ({
  telegramApi: mocks,
}));

vi.mock("../image-crop", () => ({
  cropAndUploadTelegramImage: mocks.cropAndUploadTelegramImage,
  rotateAndUploadTelegramImage: mocks.rotateAndUploadTelegramImage,
}));

beforeEach(() => {
  vi.clearAllMocks();
  mocks.getChannels.mockResolvedValue([{ id: "main", name: "Canal General" }]);
  mocks.getCategories.mockResolvedValue(["#Tecnología"]);
  mocks.generate.mockResolvedValue({
    text: "🍄 Chollo de prueba\n\n💶 Precio: 99.00 €",
    suggested_categories: [],
  });
  mocks.addCategory.mockResolvedValue(["#Tecnología"]);
  mocks.notify.mockResolvedValue({ ok: true });
  mocks.cropAndUploadTelegramImage.mockResolvedValue(
    "https://storage.test/deal-images/telegram/cropped.jpg",
  );
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

  it("guarda el recorte aceptado y usa su URL al programar", async () => {
    const user = userEvent.setup();
    const onSchedule = vi.fn().mockResolvedValue(true);

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          image_url: "https://images.test/original.jpg",
        }}
        onClose={vi.fn()}
        onSchedule={onSchedule}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    await user.click(screen.getByRole("button", { name: /^recortar$/i }));
    expect(screen.getByRole("dialog", { name: /recortar imagen/i })).toBeInTheDocument();

    const selectionLayer = screen.getByTestId("crop-selection-layer");
    vi.spyOn(selectionLayer, "getBoundingClientRect").mockReturnValue({
      x: 0,
      y: 0,
      left: 0,
      top: 0,
      right: 100,
      bottom: 100,
      width: 100,
      height: 100,
      toJSON: () => ({}),
    });
    fireEvent(
      selectionLayer,
      new MouseEvent("pointerdown", { bubbles: true, clientX: 10, clientY: 20 }),
    );
    fireEvent(
      selectionLayer,
      new MouseEvent("pointermove", { bubbles: true, clientX: 90, clientY: 80 }),
    );
    fireEvent(
      selectionLayer,
      new MouseEvent("pointerup", { bubbles: true, clientX: 90, clientY: 80 }),
    );

    await user.click(screen.getByRole("button", { name: /aceptar recorte/i }));

    await waitFor(() => expect(mocks.cropAndUploadTelegramImage).toHaveBeenCalledOnce());
    const [sourceUrl, crop] = mocks.cropAndUploadTelegramImage.mock.calls[0] ?? [];
    expect(sourceUrl).toBe("https://images.test/original.jpg");
    expect(crop).toMatchObject({ x: 0.1, y: 0.2, width: 0.8 });
    expect(crop.height).toBeCloseTo(0.6);
    expect(await screen.findByText(/recortada/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));

    await waitFor(() => expect(onSchedule).toHaveBeenCalledOnce());
    expect(onSchedule.mock.calls[0]?.[0]).toMatchObject({
      image_url: "https://storage.test/deal-images/telegram/cropped.jpg",
    });
  });

  it("descarta la selección al cancelar el recorte", async () => {
    const user = userEvent.setup();

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          image_url: "https://images.test/original.jpg",
        }}
        onClose={vi.fn()}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    await user.click(screen.getByRole("button", { name: /^recortar$/i }));
    await user.click(screen.getByRole("button", { name: /^cancelar$/i }));

    expect(screen.queryByRole("dialog", { name: /recortar imagen/i })).not.toBeInTheDocument();
    expect(mocks.cropAndUploadTelegramImage).not.toHaveBeenCalled();
  });

  it("elimina imágenes y programa solo con las restantes", async () => {
    const user = userEvent.setup();
    const onSchedule = vi.fn().mockResolvedValue(true);

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          images: [
            "https://images.test/a.jpg",
            "https://images.test/b.jpg",
            "https://images.test/c.jpg",
          ],
        }}
        onClose={vi.fn()}
        onSchedule={onSchedule}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    await user.click(screen.getByRole("button", { name: "Eliminar imagen 2" }));
    expect(screen.getByText(/imagen \(1 \/ 2\)/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /eliminar imagen actual/i }));
    expect(screen.getByRole("button", { name: /eliminar imagen actual/i })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));

    await waitFor(() => expect(onSchedule).toHaveBeenCalledOnce());
    expect(onSchedule.mock.calls[0]?.[0]).toMatchObject({
      image_url: "https://images.test/c.jpg",
      images: ["https://images.test/c.jpg"],
    });
  });

  it("no programa con más de 20 imágenes", async () => {
    const user = userEvent.setup();
    const onSchedule = vi.fn().mockResolvedValue(true);
    const images = Array.from({ length: 21 }, (_, i) => `https://images.test/${i}.jpg`);

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          images,
        }}
        onClose={vi.fn()}
        onSchedule={onSchedule}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    expect(screen.getByText(/máximo 20 imágenes para programar/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));
    expect(onSchedule).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Eliminar imagen 21" }));
    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));
    await waitFor(() => expect(onSchedule).toHaveBeenCalledOnce());
    expect(onSchedule.mock.calls[0]?.[0].images).toHaveLength(20);
  });

  it("gira la imagen 90° y sustituye la original al programar", async () => {
    const user = userEvent.setup();
    const onSchedule = vi.fn().mockResolvedValue(true);
    mocks.rotateAndUploadTelegramImage.mockResolvedValue(
      "https://storage.test/deal-images/telegram/rotated.jpg",
    );

    renderWithProviders(
      <TelegramPanel
        dealData={{
          title: "Chollo de prueba",
          current_price: 99,
          affiliate_url: "https://amazon.es/dp/B0D9WH9WLD",
          images: ["https://images.test/a.jpg", "https://images.test/b.jpg"],
        }}
        onClose={vi.fn()}
        onSchedule={onSchedule}
      />,
    );

    await screen.findByDisplayValue(/Chollo de prueba/);
    await user.click(screen.getByRole("button", { name: /girar 90°/i }));

    await waitFor(() =>
      expect(mocks.rotateAndUploadTelegramImage).toHaveBeenCalledWith("https://images.test/a.jpg"),
    );
    expect(await screen.findByText(/girada/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /programar y guardar/i }));
    await waitFor(() => expect(onSchedule).toHaveBeenCalledOnce());
    expect(onSchedule.mock.calls[0]?.[0]).toMatchObject({
      image_url: "https://storage.test/deal-images/telegram/rotated.jpg",
      images: [
        "https://storage.test/deal-images/telegram/rotated.jpg",
        "https://images.test/b.jpg",
      ],
    });
  });
});
