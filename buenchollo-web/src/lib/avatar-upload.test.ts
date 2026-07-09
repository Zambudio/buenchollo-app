import { describe, expect, it, vi, beforeEach } from "vitest";

const upload = vi.fn();
const getPublicUrl = vi.fn();
const remove = vi.fn();
vi.mock("@/integrations/supabase/client", () => ({
  supabase: { storage: { from: () => ({ upload, getPublicUrl, remove }) } },
}));

import {
  avatarPathFromPublicUrl,
  removeStoredAvatar,
  uploadAvatar,
  validateAvatarFile,
} from "./avatar-upload";

describe("avatar-upload", () => {
  beforeEach(() => {
    upload.mockReset();
    getPublicUrl.mockReset();
    remove.mockReset();
  });

  it("valida tipo y tamano maximo del avatar", () => {
    const valid = new File(["x"], "avatar.png", { type: "image/png" });
    const invalidType = new File(["x"], "avatar.txt", { type: "text/plain" });
    const tooLarge = new File([new Uint8Array(5 * 1024 * 1024 + 1)], "avatar.png", {
      type: "image/png",
    });

    expect(validateAvatarFile(valid)).toBeNull();
    expect(validateAvatarFile(invalidType)).toMatch(/JPG/);
    expect(validateAvatarFile(tooLarge)).toMatch(/5MB/);
  });

  it("extrae el path de una URL publica del bucket avatars", () => {
    expect(
      avatarPathFromPublicUrl(
        "https://project.supabase.co/storage/v1/object/public/avatars/u-1/avatar.png",
      ),
    ).toBe("u-1/avatar.png");

    expect(avatarPathFromPublicUrl("https://example.com/image.png")).toBeNull();
  });

  it("devuelve null si la URL es invalida", () => {
    expect(avatarPathFromPublicUrl("no-es-una-url")).toBeNull();
  });

  it("devuelve null sin URL", () => {
    expect(avatarPathFromPublicUrl(null)).toBeNull();
    expect(avatarPathFromPublicUrl(undefined)).toBeNull();
  });

  it("uploadAvatar sube el archivo y devuelve la URL publica", async () => {
    upload.mockResolvedValue({ error: null });
    getPublicUrl.mockReturnValue({ data: { publicUrl: "https://x/avatars/u-1/avatar-1.png" } });

    const file = new File(["x"], "avatar.png", { type: "image/png" });
    const url = await uploadAvatar("u-1", file);

    expect(url).toBe("https://x/avatars/u-1/avatar-1.png");
    expect(upload).toHaveBeenCalledWith(
      expect.stringMatching(/^u-1\/avatar-\d+-\w+\.png$/),
      file,
      expect.objectContaining({ contentType: "image/png", upsert: false }),
    );
  });

  it("uploadAvatar propaga el error de validacion sin llamar a supabase", async () => {
    const invalidFile = new File(["x"], "avatar.txt", { type: "text/plain" });
    await expect(uploadAvatar("u-1", invalidFile)).rejects.toThrow(/JPG/);
    expect(upload).not.toHaveBeenCalled();
  });

  it("uploadAvatar propaga el error de supabase storage", async () => {
    upload.mockResolvedValue({ error: new Error("boom") });
    const file = new File(["x"], "avatar.png", { type: "image/png" });
    await expect(uploadAvatar("u-1", file)).rejects.toThrow("boom");
  });

  it("removeStoredAvatar borra el path extraido de la URL", async () => {
    remove.mockResolvedValue({ error: null });
    await removeStoredAvatar("https://x/storage/v1/object/public/avatars/u-1/avatar.png");
    expect(remove).toHaveBeenCalledWith(["u-1/avatar.png"]);
  });

  it("removeStoredAvatar no llama a supabase sin path valido", async () => {
    await removeStoredAvatar(null);
    expect(remove).not.toHaveBeenCalled();
  });
});
