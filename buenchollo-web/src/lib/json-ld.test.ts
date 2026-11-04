import { describe, expect, it } from "vitest";
import { serializeJsonLd } from "./json-ld";

const LINE_SEPARATOR = String.fromCharCode(0x2028);

describe("serializeJsonLd", () => {
  const evil = {
    name: "</script><img src=x onerror=alert(1)>",
    description: `a & b <!-- c --> ${LINE_SEPARATOR} fin`,
  };

  it("no deja ninguna secuencia que el HTML pueda interpretar", () => {
    const out = serializeJsonLd(evil);
    for (const ch of ["<", ">", "&", LINE_SEPARATOR]) expect(out).not.toContain(ch);
    expect(out).toContain("\\u003c/script\\u003e");
  });

  it("sigue siendo JSON equivalente al original", () => {
    expect(JSON.parse(serializeJsonLd(evil))).toEqual(evil);
  });
});
