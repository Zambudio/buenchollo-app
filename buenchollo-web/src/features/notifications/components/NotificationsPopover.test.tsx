import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { NotificationsPopover } from "./NotificationsPopover";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({
  useUnreadNotifications: vi.fn(),
  useNotificationsList: vi.fn(),
  useMarkNotificationsRead: vi.fn(),
  useMarkNotificationRead: vi.fn(),
  mockNavigate: vi.fn(),
}));

vi.mock("@tanstack/react-router", () => ({
  useNavigate: () => mocks.mockNavigate,
}));

vi.mock("@/features/notifications/hooks/useNotifications", () => ({
  useUnreadNotifications: mocks.useUnreadNotifications,
  useNotificationsList: mocks.useNotificationsList,
  useMarkNotificationsRead: mocks.useMarkNotificationsRead,
  useMarkNotificationRead: mocks.useMarkNotificationRead,
}));

describe("NotificationsPopover", () => {
  const mockMutate = vi.fn();
  const mockMutateOne = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mocks.useUnreadNotifications.mockReturnValue({ data: 0 });
    mocks.useNotificationsList.mockReturnValue({
      data: [],
      isLoading: false,
    });
    mocks.useMarkNotificationsRead.mockReturnValue({
      mutate: mockMutate,
      isPending: false,
    });
    mocks.useMarkNotificationRead.mockReturnValue({
      mutate: mockMutateOne,
      isPending: false,
    });
  });

  it("renderiza el botón de notificaciones con accesibilidad", () => {
    renderWithProviders(<NotificationsPopover />);
    expect(screen.getByRole("button", { name: /notificaciones/i })).toBeInTheDocument();
  });

  it("muestra el badge cuando hay notificaciones sin leer", () => {
    mocks.useUnreadNotifications.mockReturnValue({ data: 3 });
    renderWithProviders(<NotificationsPopover />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("muestra '9+' cuando hay más de 9 notificaciones sin leer", () => {
    mocks.useUnreadNotifications.mockReturnValue({ data: 12 });
    renderWithProviders(<NotificationsPopover />);
    expect(screen.getByText("9+")).toBeInTheDocument();
  });

  it("abre el popup al hacer click y muestra el estado vacío si no hay items", async () => {
    const user = userEvent.setup();
    renderWithProviders(<NotificationsPopover />);

    await user.click(screen.getByRole("button", { name: /notificaciones/i }));

    expect(screen.getByRole("heading", { name: /notificaciones/i })).toBeInTheDocument();
    expect(screen.getByText(/sin notificaciones por ahora/i)).toBeInTheDocument();
  });

  it("muestra el botón 'Marcar todas como leídas' cuando unread > 0 y ejecuta mutate al hacer click", async () => {
    const user = userEvent.setup();
    mocks.useUnreadNotifications.mockReturnValue({ data: 2 });
    mocks.useNotificationsList.mockReturnValue({
      data: [
        {
          id: "n-1",
          title: "Alerta: Cámara",
          body: "Nuevo chollo: GoPro Hero 4K",
          link_url: "/chollo/gopro-hero-4k",
          deal_id: "d-1",
          is_read: false,
          created_at: "2026-08-07T12:00:00Z",
        },
      ],
      isLoading: false,
    });

    renderWithProviders(<NotificationsPopover />);
    await user.click(screen.getByRole("button", { name: /notificaciones/i }));

    const markAllBtn = screen.getByRole("button", { name: /marcar todas como leídas/i });
    expect(markAllBtn).toBeInTheDocument();

    await user.click(markAllBtn);
    expect(mockMutate).toHaveBeenCalledTimes(1);
  });

  it("NO muestra el botón 'Marcar todas como leídas' cuando unread es 0", async () => {
    const user = userEvent.setup();
    mocks.useUnreadNotifications.mockReturnValue({ data: 0 });
    mocks.useNotificationsList.mockReturnValue({
      data: [
        {
          id: "n-1",
          title: "Alerta: Cámara",
          body: "Cámara instantánea Polaroid",
          link_url: "/chollo/polaroid",
          deal_id: "d-1",
          is_read: true,
          created_at: "2026-08-06T10:00:00Z",
        },
      ],
      isLoading: false,
    });

    renderWithProviders(<NotificationsPopover />);
    await user.click(screen.getByRole("button", { name: /notificaciones/i }));

    expect(screen.getByText("Alerta: Cámara")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /marcar todas como leídas/i }),
    ).not.toBeInTheDocument();
  });

  it("al hacer click en una notificación no leída navega al chollo, la marca como leída y cierra el popup", async () => {
    const user = userEvent.setup();
    mocks.useNotificationsList.mockReturnValue({
      data: [
        {
          id: "n-1",
          title: "Alerta: Samsung",
          body: "Nuevo chollo: Cargador USB-C 30W",
          link_url: "/chollo/cargador-samsung-30w",
          deal_id: "d-2",
          is_read: false,
          created_at: "2026-08-06T08:00:00Z",
        },
      ],
      isLoading: false,
    });

    renderWithProviders(<NotificationsPopover />);
    await user.click(screen.getByRole("button", { name: /notificaciones/i }));

    const itemBtn = screen.getByRole("button", { name: /alerta: samsung/i });
    await user.click(itemBtn);

    expect(mocks.mockNavigate).toHaveBeenCalledWith({ to: "/chollo/cargador-samsung-30w" });
    expect(mockMutateOne).toHaveBeenCalledWith("n-1");
  });

  it("al hacer click en una notificación ya leída navega pero no vuelve a marcarla", async () => {
    const user = userEvent.setup();
    mocks.useNotificationsList.mockReturnValue({
      data: [
        {
          id: "n-2",
          title: "Alerta: Polaroid",
          body: "Nuevo chollo: Cámara instantánea",
          link_url: "/chollo/polaroid",
          deal_id: "d-3",
          is_read: true,
          created_at: "2026-08-06T08:00:00Z",
        },
      ],
      isLoading: false,
    });

    renderWithProviders(<NotificationsPopover />);
    await user.click(screen.getByRole("button", { name: /notificaciones/i }));

    const itemBtn = screen.getByRole("button", { name: /alerta: polaroid/i });
    await user.click(itemBtn);

    expect(mocks.mockNavigate).toHaveBeenCalledWith({ to: "/chollo/polaroid" });
    expect(mockMutateOne).not.toHaveBeenCalled();
  });
});
