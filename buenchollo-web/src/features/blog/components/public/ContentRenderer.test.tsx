import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ContentRenderer } from "./ContentRenderer";
import type { JSONContent } from "@tiptap/core";

vi.mock("@/services/api/deals", () => ({
  dealsService: { trackClick: vi.fn().mockResolvedValue(1) },
}));

describe("ContentRenderer", () => {
  it("renderiza párrafos, negrita y encabezados con id ancla", () => {
    const doc: JSONContent = {
      type: "doc",
      content: [
        { type: "heading", attrs: { level: 2 }, content: [{ type: "text", text: "Introducción" }] },
        {
          type: "paragraph",
          content: [
            { type: "text", text: "texto normal " },
            { type: "text", text: "en negrita", marks: [{ type: "bold" }] },
          ],
        },
      ],
    };
    render(<ContentRenderer doc={doc} />);
    const heading = screen.getByRole("heading", { level: 2, name: "Introducción" });
    expect(heading).toHaveAttribute("id", "introduccion");
    expect(screen.getByText("en negrita").tagName).toBe("STRONG");
  });

  it("los enlaces externos llevan rel=noopener noreferrer y los internos no", () => {
    const doc: JSONContent = {
      type: "doc",
      content: [
        {
          type: "paragraph",
          content: [
            {
              type: "text",
              text: "externo",
              marks: [{ type: "link", attrs: { href: "https://example.com" } }],
            },
            {
              type: "text",
              text: "interno",
              marks: [{ type: "link", attrs: { href: "/chollo/x" } }],
            },
          ],
        },
      ],
    };
    render(<ContentRenderer doc={doc} />);
    expect(screen.getByText("externo")).toHaveAttribute("rel", "noopener noreferrer");
    expect(screen.getByText("interno")).not.toHaveAttribute("rel");
  });

  it("renderiza un bloque callout con su etiqueta de variante", () => {
    const doc: JSONContent = {
      type: "doc",
      content: [
        {
          type: "callout",
          attrs: { variant: "warning" },
          content: [{ type: "paragraph", content: [{ type: "text", text: "Cuidado" }] }],
        },
      ],
    };
    render(<ContentRenderer doc={doc} />);
    expect(screen.getByRole("note", { name: "Advertencia" })).toBeInTheDocument();
    expect(screen.getByText("Cuidado")).toBeInTheDocument();
  });

  it.each([
    ["left", "0px", "auto"],
    ["center", "auto", "auto"],
    ["right", "auto", "0px"],
  ])("respeta la alineación %s de las imágenes", (align, marginLeft, marginRight) => {
    const doc: JSONContent = {
      type: "doc",
      content: [
        {
          type: "image",
          attrs: {
            src: "https://example.com/producto.webp",
            alt: `Imagen ${align}`,
            align,
            width: "normal",
          },
        },
      ],
    };

    render(<ContentRenderer doc={doc} />);

    expect(screen.getByRole("img", { name: `Imagen ${align}` })).toHaveStyle({
      display: "block",
      marginLeft,
      marginRight,
    });
  });

  it("resuelve un bloque de producto en modo chollo usando el mapa de products", () => {
    const doc: JSONContent = {
      type: "doc",
      content: [
        {
          type: "productRecommendation",
          attrs: {
            mode: "deal",
            deal_id: "d1",
            name: null,
            image_url: null,
            affiliate_url: null,
            note: null,
            button_text: null,
            badge: null,
          },
        },
      ],
    };
    render(
      <ContentRenderer
        doc={doc}
        products={{
          d1: {
            id: "d1",
            title: "Producto resuelto",
            slug: "producto-resuelto",
            image_url: null,
            affiliate_url: "https://amazon.es/dp/d1",
            store_name: "Amazon",
            current_price: 10,
            previous_price: null,
            discount_percentage: null,
            is_active: true,
          },
        }}
      />,
    );
    expect(screen.getByText("Producto resuelto")).toBeInTheDocument();
  });

  it("no renderiza nada para tipos de nodo no soportados", () => {
    const doc: JSONContent = { type: "doc", content: [{ type: "iframe", attrs: { src: "x" } }] };
    const { container } = render(<ContentRenderer doc={doc} />);
    expect(container.textContent).toBe("");
  });
});
