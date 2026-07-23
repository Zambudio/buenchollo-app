import { describe, expect, it } from "vitest";
import {
  countWords,
  extractPlainText,
  hasAffiliateBlocks,
  isContentEmpty,
  readingTimeMinutes,
} from "./content";
import type { JSONContent } from "@tiptap/core";

function doc(...content: JSONContent[]): JSONContent {
  return { type: "doc", content };
}

function paragraph(text: string): JSONContent {
  return { type: "paragraph", content: [{ type: "text", text }] };
}

describe("extractPlainText / countWords", () => {
  it("extrae el texto plano de párrafos anidados en listas", () => {
    const document = doc({
      type: "bulletList",
      content: [{ type: "listItem", content: [paragraph("Hola mundo")] }],
    });
    expect(extractPlainText(document).trim()).toBe("Hola mundo");
    expect(countWords(extractPlainText(document))).toBe(2);
  });
});

describe("readingTimeMinutes", () => {
  it("es 0 si no hay palabras y al menos 1 si hay texto", () => {
    expect(readingTimeMinutes(0)).toBe(0);
    expect(readingTimeMinutes(10)).toBe(1);
    expect(readingTimeMinutes(400)).toBe(2);
  });
});

describe("hasAffiliateBlocks", () => {
  it("detecta bloques de producto en cualquier profundidad", () => {
    expect(hasAffiliateBlocks(doc(paragraph("sin bloques")))).toBe(false);
    const withProduct = doc({ type: "productRecommendation", attrs: { mode: "manual" } });
    expect(hasAffiliateBlocks(withProduct)).toBe(true);
  });
});

describe("isContentEmpty", () => {
  it("considera vacío un documento sin texto", () => {
    expect(isContentEmpty(doc())).toBe(true);
    expect(isContentEmpty(doc(paragraph("   ")))).toBe(true);
    expect(isContentEmpty(doc(paragraph("hola")))).toBe(false);
  });
});
