import { describe, expect, it } from "vitest";
import {
  absoluteUrl,
  DEFAULT_OG_IMAGE,
  pageHead,
  privatePageHead,
  ROBOTS_INDEX,
  ROBOTS_NOINDEX,
  withBrand,
} from "./head";
import { clampDescription, clampText, priceText } from "./text";

function metaValue(head: ReturnType<typeof pageHead>, key: string) {
  for (const tag of head.meta) {
    if ("name" in tag && tag.name === key) return tag.content;
    if ("property" in tag && tag.property === key) return tag.content;
  }
  return undefined;
}

describe("text", () => {
  it("clampText deja el texto corto intacto y normaliza espacios y Markdown", () => {
    expect(clampText("  **Hola**\n mundo  ", 50)).toBe("Hola mundo");
  });

  it("clampText corta en una palabra y añade puntos suspensivos", () => {
    const text = clampText("Auriculares inalámbricos con cancelación de ruido activa", 30);
    expect(text.endsWith("…")).toBe(true);
    expect(text.length).toBeLessThanOrEqual(30);
    expect(text).not.toMatch(/\s…$/);
  });

  it("clampText corta a mitad de palabra si no hay un espacio razonable", () => {
    expect(clampText("Supercalifragilisticoespialidoso", 10)).toBe("Supercali…");
  });

  it("clampDescription limita a 158 caracteres", () => {
    expect(clampDescription("a ".repeat(200)).length).toBeLessThanOrEqual(158);
  });

  it("priceText usa formato español", () => {
    expect(priceText(199)).toBe("199 €");
    expect(priceText(17.1)).toBe("17,10 €");
  });
});

describe("head", () => {
  it("absoluteUrl respeta URLs completas y completa rutas", () => {
    expect(absoluteUrl("https://otro.com/x")).toBe("https://otro.com/x");
    expect(absoluteUrl("/blog")).toBe("https://buenchollotech.com/blog");
    expect(absoluteUrl("blog")).toBe("https://buenchollotech.com/blog");
  });

  it("withBrand añade la marca una sola vez", () => {
    expect(withBrand("Contacto")).toBe("Contacto | BuenChollo Tech");
    expect(withBrand("Contacto | BuenChollo Tech")).toBe("Contacto | BuenChollo Tech");
  });

  it("pageHead publica todas las etiquetas de una página indexable", () => {
    const head = pageHead({
      title: withBrand("Chollos de audio"),
      description: "Ofertas de audio",
      path: "/categoria/audio",
      jsonLd: [{ "@type": "CollectionPage" }],
      extraMeta: [{ property: "article:section", content: "Audio" }],
    });
    expect(head.meta[0]).toEqual({ title: "Chollos de audio | BuenChollo Tech" });
    expect(metaValue(head, "robots")).toBe(ROBOTS_INDEX);
    expect(metaValue(head, "og:title")).toBe("Chollos de audio");
    expect(metaValue(head, "og:url")).toBe("https://buenchollotech.com/categoria/audio");
    expect(metaValue(head, "og:type")).toBe("website");
    expect(metaValue(head, "og:image")).toBe(DEFAULT_OG_IMAGE);
    expect(metaValue(head, "twitter:description")).toBe("Ofertas de audio");
    expect(metaValue(head, "article:section")).toBe("Audio");
    expect(head.links).toEqual([
      { rel: "canonical", href: "https://buenchollotech.com/categoria/audio" },
    ]);
    expect(JSON.parse(head.scripts[0]!.children)).toEqual({
      "@context": "https://schema.org",
      "@graph": [{ "@type": "CollectionPage" }],
    });
  });

  it("pageHead con noindex, imagen propia y sin JSON-LD", () => {
    const head = pageHead({
      title: "X",
      description: "Y",
      path: "/x",
      image: "/og/x.png",
      imageAlt: "Alt",
      type: "article",
      noindex: true,
    });
    expect(metaValue(head, "robots")).toBe(ROBOTS_NOINDEX);
    expect(metaValue(head, "og:image")).toBe("https://buenchollotech.com/og/x.png");
    expect(metaValue(head, "og:image:alt")).toBe("Alt");
    expect(metaValue(head, "og:type")).toBe("article");
    expect(head.scripts).toEqual([]);
  });

  it("privatePageHead queda fuera del índice", () => {
    expect(privatePageHead("Perfil", "Tu cuenta").meta).toEqual([
      { title: "Perfil | BuenChollo Tech" },
      { name: "description", content: "Tu cuenta" },
      { name: "robots", content: "noindex, nofollow" },
    ]);
  });
});
