import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { renderWithProviders } from "@/test/utils";
import { BlogPostCard } from "./BlogPostCard";
import type { BlogPostCard as BlogPostCardData } from "@/services/api/blog";

vi.mock("@tanstack/react-router", () => ({
  Link: ({
    children,
    to,
    params,
  }: {
    children: React.ReactNode;
    to: string;
    params?: Record<string, string>;
  }) => {
    const href = params
      ? Object.entries(params).reduce((acc, [k, v]) => acc.replace(`$${k}`, v), to)
      : to;
    return <a href={href}>{children}</a>;
  },
}));

function buildPost(overrides: Partial<BlogPostCardData> = {}): BlogPostCardData {
  return {
    id: "1",
    title: "Guía de auriculares 2026",
    slug: "guia-auriculares-2026",
    excerpt: "Un resumen de las mejores opciones del mercado.",
    cover_image_url: "https://cdn.example.com/cover.png",
    cover_image_alt: "Auriculares sobre una mesa",
    tags: [],
    is_featured: false,
    published_at: "2026-07-01T10:00:00Z",
    reading_time_minutes: 5,
    category: {
      id: "c1",
      name: "Auriculares",
      slug: "auriculares",
      description: null,
      is_active: true,
      sort_order: 0,
    },
    ...overrides,
  };
}

describe("BlogPostCard", () => {
  it("renderiza título, categoría, extracto y enlaza a /blog/{slug} en un único enlace", () => {
    const post = buildPost();
    renderWithProviders(<BlogPostCard post={post} />);

    expect(screen.getByText("Guía de auriculares 2026")).toBeInTheDocument();
    expect(screen.getByText("Auriculares")).toBeInTheDocument();
    expect(screen.getByText(/mejores opciones/)).toBeInTheDocument();

    const links = screen.getAllByRole("link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/blog/guia-auriculares-2026");
  });

  it("muestra el tiempo de lectura", () => {
    renderWithProviders(<BlogPostCard post={buildPost({ reading_time_minutes: 8 })} />);
    expect(screen.getByText(/8 min/)).toBeInTheDocument();
  });
});
