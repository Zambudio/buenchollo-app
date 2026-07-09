import { describe, expect, it } from "vitest";
import { googleAvatarUrl, googleDisplayName } from "./google-profile";
import type { User } from "@supabase/supabase-js";

function buildUser(overrides: Partial<User> = {}): User {
  return {
    id: "u-1",
    app_metadata: {},
    user_metadata: {},
    aud: "authenticated",
    created_at: "",
    ...overrides,
  } as User;
}

describe("googleDisplayName", () => {
  it("usa full_name de user_metadata si está disponible", () => {
    const user = buildUser({ user_metadata: { full_name: "Pedro Zambudio" } });
    expect(googleDisplayName(user)).toBe("Pedro Zambudio");
  });

  it("cae a identity_data cuando user_metadata no trae nombre", () => {
    const user = buildUser({
      user_metadata: {},
      identities: [
        { identity_data: { name: "Pedro I." } } as unknown as NonNullable<
          User["identities"]
        >[number],
      ],
    });
    expect(googleDisplayName(user)).toBe("Pedro I.");
  });

  it("cae al fallback explícito y luego a la parte local del email", () => {
    const user = buildUser({ email: "pedro@example.com" });
    expect(googleDisplayName(user, "Fallback")).toBe("Fallback");
    expect(googleDisplayName(user)).toBe("pedro");
  });

  it("devuelve cadena vacía sin usuario", () => {
    expect(googleDisplayName(null)).toBe("");
  });
});

describe("googleAvatarUrl", () => {
  it("usa avatar_url de user_metadata si está disponible", () => {
    const user = buildUser({ user_metadata: { avatar_url: "https://google/a.png" } });
    expect(googleAvatarUrl(user)).toBe("https://google/a.png");
  });

  it("cae a picture de identity_data cuando no hay avatar_url en user_metadata", () => {
    const user = buildUser({
      user_metadata: {},
      identities: [
        { identity_data: { picture: "https://google/b.png" } } as unknown as NonNullable<
          User["identities"]
        >[number],
      ],
    });
    expect(googleAvatarUrl(user)).toBe("https://google/b.png");
  });

  it("devuelve el fallback cuando no hay avatar disponible", () => {
    expect(googleAvatarUrl(buildUser(), "https://fallback")).toBe("https://fallback");
    expect(googleAvatarUrl(null)).toBe("");
  });
});
