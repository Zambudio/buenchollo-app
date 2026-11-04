import { describe, expect, it } from "vitest";
import { loginSearch, safeRedirect } from "@/lib/safe-redirect";

describe("safeRedirect", () => {
  it("acepta rutas relativas con query", () => {
    expect(safeRedirect("/publicar")).toBe("/publicar");
    expect(safeRedirect("/publicar?url=https%3A%2F%2Fx.es%2Fa%3Fb%3D1")).toBe(
      "/publicar?url=https%3A%2F%2Fx.es%2Fa%3Fb%3D1",
    );
  });

  it.each([
    ["//evil.com"],
    ["/\\evil.com"],
    ["https://evil.com"],
    ["javascript:alert(1)"],
    ["evil.com"],
    [""],
    ["/\t/evil.com"],
    ["/\n/evil.com"],
    ["/a\\b"],
    ["/" + "a".repeat(2100)],
  ])("rechaza %j", (v) => {
    expect(safeRedirect(v)).toBe("/");
  });

  it("rechaza valores no string", () => {
    expect(safeRedirect(undefined)).toBe("/");
    expect(safeRedirect(null)).toBe("/");
    expect(safeRedirect(42)).toBe("/");
  });
});

describe("loginSearch", () => {
  it("omite redirect cuando no es seguro o es la home", () => {
    expect(loginSearch(undefined)).toEqual({});
    expect(loginSearch("//evil.com")).toEqual({});
    expect(loginSearch("/")).toEqual({});
  });
  it("conserva redirect seguro", () => {
    expect(loginSearch("/publicar")).toEqual({ redirect: "/publicar" });
  });
});
