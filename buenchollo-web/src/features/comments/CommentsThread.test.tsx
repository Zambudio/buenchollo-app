import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CommentsThread, type CommentsThreadApi } from "./CommentsThread";

const auth = vi.hoisted(() => ({
  value: { user: { id: "u1" } as { id: string } | null, isAdmin: false },
}));
vi.mock("@/hooks/useAuth", () => ({ useAuth: () => auth.value }));
vi.mock("sonner", () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

const COMMENT = {
  id: "c1",
  user_id: "otro",
  parent_id: null,
  content: "Spam",
  votes_up: 0,
  votes_down: 0,
  created_at: "2026-11-18T10:00:00Z",
  author: { display_name: "otro", avatar_url: null },
  my_vote: 0,
};

function api(): CommentsThreadApi {
  return {
    list: vi.fn().mockResolvedValue([COMMENT]),
    create: vi.fn(),
    remove: vi.fn().mockResolvedValue(undefined),
    adminRemove: vi.fn().mockResolvedValue(undefined),
    vote: vi.fn(),
  };
}

beforeEach(() => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
});

describe("CommentsThread", () => {
  it("un usuario normal no puede borrar comentarios ajenos", async () => {
    auth.value = { user: { id: "u1" }, isAdmin: false };
    render(<CommentsThread targetId="d1" api={api()} subject="este chollo" />);
    expect(await screen.findByText("Spam")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Eliminar comentario" })).not.toBeInTheDocument();
    expect(screen.getByPlaceholderText("Comparte tu opinión sobre este chollo...")).toBeEnabled();
  });

  it("un admin modera comentarios ajenos con la ruta de moderación", async () => {
    auth.value = { user: { id: "admin" }, isAdmin: true };
    const calls = api();
    const onCountChange = vi.fn();
    render(
      <CommentsThread
        targetId="d1"
        api={calls}
        subject="este artículo"
        onCountChange={onCountChange}
      />,
    );
    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Eliminar comentario" }));
    await waitFor(() => expect(calls.adminRemove).toHaveBeenCalledWith("c1"));
    expect(calls.remove).not.toHaveBeenCalled();
    expect(onCountChange).toHaveBeenCalled();
  });

  it("el autor borra su comentario con la ruta propia", async () => {
    auth.value = { user: { id: "otro" }, isAdmin: false };
    const calls = api();
    render(<CommentsThread targetId="d1" api={calls} subject="este chollo" />);
    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Eliminar comentario" }));
    await waitFor(() => expect(calls.remove).toHaveBeenCalledWith("c1"));
    expect(calls.adminRemove).not.toHaveBeenCalled();
  });
});
