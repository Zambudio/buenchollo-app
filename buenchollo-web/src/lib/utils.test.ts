/** Smoke test del setup de Vitest: verifica que jsdom + globals están
 *  cargados antes de empezar con los tests de verdad. Si esto falla,
 *  el resto del suite tampoco arrancará. */
import { describe, expect, it } from "vitest";
import { cn } from "@/lib/utils";

describe("cn (tailwind-merge helper)", () => {
  it("concatena clases truthy y descarta falsy", () => {
    expect(cn("a", undefined, false, "b")).toBe("a b");
  });

  it("deduplica conflictos de tailwind quedándose con el último", () => {
    // p-2 y p-4 son utilidades incompatibles → twMerge resuelve por el último.
    expect(cn("p-2", "p-4")).toBe("p-4");
  });
});
