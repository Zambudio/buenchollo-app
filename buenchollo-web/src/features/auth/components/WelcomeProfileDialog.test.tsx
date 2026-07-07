import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { WelcomeProfileDialog } from "./WelcomeProfileDialog";
import { renderWithProviders } from "@/test/utils";

const mocks = vi.hoisted(() => ({
  useAuth: vi.fn(),
  getMyProfile: vi.fn(),
  updateMyProfile: vi.fn(),
  refreshMe: vi.fn(),
}));

vi.mock("@/hooks/useAuth", () => ({ useAuth: mocks.useAuth }));

vi.mock("@/services/api/auth", () => ({
  authApi: {
    getMyProfile: mocks.getMyProfile,
    updateMyProfile: mocks.updateMyProfile,
  },
}));

beforeEach(() => {
  mocks.refreshMe.mockResolvedValue(undefined);
  mocks.getMyProfile.mockResolvedValue({
    user_id: "u-1",
    display_name: null,
    bio: "",
    avatar_url: null,
    username: null,
  });
  mocks.updateMyProfile.mockResolvedValue({
    user_id: "u-1",
    display_name: "Pedro Google",
    bio: "",
    avatar_url: "https://example.com/avatar.png",
    username: null,
  });
  mocks.useAuth.mockReturnValue({
    user: {
      id: "u-1",
      email: "pedro@example.com",
      user_metadata: {
        full_name: "Pedro Google",
        avatar_url: "https://example.com/avatar.png",
      },
    },
    me: {
      user_id: "u-1",
      email: "pedro@example.com",
      roles: ["user"],
      is_admin: false,
      has_profile: true,
      needs_onboarding: true,
      display_name: null,
      avatar_url: null,
      username: null,
    },
    loading: false,
    refreshMe: mocks.refreshMe,
  });
});

describe("WelcomeProfileDialog", () => {
  it("precarga datos de Google y confirma el perfil inicial", async () => {
    const user = userEvent.setup();

    renderWithProviders(<WelcomeProfileDialog />);

    const input = await screen.findByLabelText(/nombre visible/i);
    await waitFor(() => expect(input).toHaveValue("Pedro Google"));

    await user.click(screen.getByRole("button", { name: /confirmar nombre/i }));

    await waitFor(() => {
      expect(mocks.updateMyProfile).toHaveBeenCalledWith({
        display_name: "Pedro Google",
        bio: "",
        avatar_url: "https://example.com/avatar.png",
      });
    });
    expect(mocks.refreshMe).toHaveBeenCalledOnce();
  });
});
