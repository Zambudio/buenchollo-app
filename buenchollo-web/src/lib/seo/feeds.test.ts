import { describe, expect, it } from "vitest";
import { escapeXml } from "@/lib/xml";
import { buildLlmsTxt } from "./llms";
import { renderRss } from "./rss";

describe("buildLlmsTxt", () => {
  it("resume el sitio con categorías, chollos con precio, guías y FAQ", () => {
    const text = buildLlmsTxt({
      deals: [
        {
          slug: "sony",
          title: "Sony\nWH-1000XM5",
          current_price: 279.99,
          previous_price: 419,
          discount_percentage: 33,
          store: { name: "Amazon" },
        },
        {
          slug: "cable",
          title: "Cable",
          current_price: 9,
          previous_price: null,
          discount_percentage: null,
        },
      ],
      categories: [{ slug: "audio", name: "Audio" }],
      posts: [
        { slug: "guia", title: "Guía", excerpt: "Cómo elegir\nauriculares" },
        { slug: "otra", title: "Otra" },
      ],
      generatedAt: new Date("2026-11-18T10:00:00Z"),
    });
    expect(text.startsWith("# BuenChollo Tech\n\n> ")).toBe(true);
    expect(text).toContain("Actualizado: 2026-11-18.");
    expect(text).toContain("- [Chollos de Audio](https://buenchollotech.com/categoria/audio)");
    expect(text).toContain(
      "- [Sony WH-1000XM5](https://buenchollotech.com/chollo/sony): 279,99 €, antes 419 €, -33 % en Amazon",
    );
    expect(text).toContain("- [Cable](https://buenchollotech.com/chollo/cable): 9 €\n");
    expect(text).toContain("(https://buenchollotech.com/blog/guia): Cómo elegir auriculares");
    expect(text).toContain("- [Otra](https://buenchollotech.com/blog/otra)\n");
    expect(text).toContain("## Preguntas frecuentes");
    expect(text).toContain("contacto@buenchollotech.com");
  });

  it("omite las secciones sin datos", () => {
    const text = buildLlmsTxt({ deals: [], categories: [], posts: [], generatedAt: new Date() });
    expect(text).not.toContain("## Últimos chollos activos");
    expect(text).not.toContain("## Categorías con chollos");
    expect(text).not.toContain("## Guías del blog");
  });
});

describe("renderRss", () => {
  it("genera un RSS 2.0 válido con enlace propio y escapado", () => {
    const xml = renderRss({
      title: "Chollos & más",
      link: "https://buenchollotech.com/",
      selfUrl: "https://buenchollotech.com/rss.xml",
      description: "Feed",
      items: [
        {
          title: "Monitor <27>",
          url: "https://buenchollotech.com/chollo/m",
          description: "Desc",
          publishedAt: "2026-11-18T15:00:00Z",
          category: "Informática",
        },
        { title: "Sin fecha", url: "https://buenchollotech.com/chollo/s", publishedAt: "mal" },
      ],
    });
    expect(xml).toContain("<title>Chollos &amp; más</title>");
    expect(xml).toContain('rel="self"');
    expect(xml).toContain("<title>Monitor &lt;27&gt;</title>");
    expect(xml).toContain("<pubDate>Wed, 18 Nov 2026 15:00:00 GMT</pubDate>");
    expect(xml).toContain("<category>Informática</category>");
    expect(xml.match(/<pubDate>/g)).toHaveLength(1);
  });

  it("escapeXml escapa los cinco caracteres reservados", () => {
    expect(escapeXml(`<a href="x">'&'</a>`)).toBe(
      "&lt;a href=&quot;x&quot;&gt;&apos;&amp;&apos;&lt;/a&gt;",
    );
  });
});
