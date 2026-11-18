import { afterEach, describe, expect, it, vi } from "vitest";
import { getLocalStorage, readLocal, writeLocal } from "./storage";

afterEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
});

describe("storage", () => {
  it("lee y escribe en localStorage cuando está disponible", () => {
    writeLocal("k", "v");
    expect(readLocal("k")).toBe("v");
    expect(getLocalStorage()).toBe(window.localStorage);
  });

  it("no lanza si el navegador bloquea el almacenamiento", () => {
    vi.spyOn(window, "localStorage", "get").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    expect(getLocalStorage()).toBeNull();
    expect(readLocal("k")).toBeNull();
    expect(() => writeLocal("k", "v")).not.toThrow();
  });

  it("no lanza si escribir falla (cuota llena)", () => {
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new DOMException("lleno", "QuotaExceededError");
    });
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new DOMException("bloqueado", "SecurityError");
    });
    expect(() => writeLocal("k", "v")).not.toThrow();
    expect(readLocal("k")).toBeNull();
  });
});
