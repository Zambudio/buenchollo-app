import { describe, expect, it } from "vitest";
import { extractDomain, isAllowedAffiliateDomain } from "./affiliateDomains";

describe("extractDomain", () => {
  it("extrae el host sin www", () => {
    expect(extractDomain("https://www.amazon.es/dp/X")).toBe("amazon.es");
    expect(extractDomain("https://pccomponentes.com/x")).toBe("pccomponentes.com");
  });

  it("devuelve vacío para URLs inválidas", () => {
    expect(extractDomain("no-es-una-url")).toBe("");
  });
});

describe("isAllowedAffiliateDomain", () => {
  it("acepta dominios de la allowlist", () => {
    expect(isAllowedAffiliateDomain("https://amazon.es/dp/X")).toBe(true);
    expect(isAllowedAffiliateDomain("https://s.click.aliexpress.com/x")).toBe(true);
  });

  it("rechaza dominios fuera de la allowlist", () => {
    expect(isAllowedAffiliateDomain("https://sospechoso.example/x")).toBe(false);
  });
});
