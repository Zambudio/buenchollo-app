import { describe, expect, it } from "vitest";
import { avatarPathFromPublicUrl, validateAvatarFile } from "./avatar-upload";

describe("avatar-upload", () => {
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
});
