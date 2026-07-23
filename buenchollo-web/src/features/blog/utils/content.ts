/** Utilidades puras sobre el documento Tiptap, para feedback inmediato en
 * el editor (contador de palabras, tiempo de lectura, detección de bloques
 * afiliados). El backend recalcula/valida todo de forma autoritativa. */
import type { JSONContent } from "@tiptap/core";

const READING_WPM = 200;

function* walk(node: JSONContent): Generator<JSONContent> {
  yield node;
  for (const child of node.content ?? []) yield* walk(child);
}

export function extractPlainText(doc: JSONContent): string {
  const parts: string[] = [];
  for (const node of walk(doc)) {
    if (node.type === "text" && typeof node.text === "string") parts.push(node.text);
  }
  return parts.join(" ");
}

export function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

export function readingTimeMinutes(wordCount: number): number {
  if (!wordCount) return 0;
  return Math.max(1, Math.round(wordCount / READING_WPM));
}

export function hasAffiliateBlocks(doc: JSONContent): boolean {
  for (const node of walk(doc)) {
    if (node.type === "productRecommendation") return true;
  }
  return false;
}

export function isContentEmpty(doc: JSONContent): boolean {
  return extractPlainText(doc).trim().length === 0;
}
