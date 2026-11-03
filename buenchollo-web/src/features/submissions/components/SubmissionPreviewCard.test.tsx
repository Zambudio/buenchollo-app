import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SubmissionPreviewCard } from "./SubmissionPreviewCard";

vi.mock("@tanstack/react-router", () => ({
  Link: ({ children, to }: { children: React.ReactNode; to: string }) => (
    <a href={to}>{children}</a>
  ),
}));

describe("SubmissionPreviewCard", () => {
  it("pinta la tarjeta del listado sin enlaces ni acciones", () => {
    const { container } = render(
      <SubmissionPreviewCard
        title="Monitor 4K"
        currentPrice={199.9}
        previousPrice={299.9}
        images={["https://cdn/a.webp", "https://cdn/b.webp"]}
        storeName="PcComponentes"
      />,
    );
    const article = container.querySelector("article.deal-card")!;
    expect(article).toBeInTheDocument();
    expect(article.hasAttribute("inert")).toBe(true);
    expect(container.querySelectorAll("a[href]")).toHaveLength(0);
    expect(within(article as HTMLElement).getByText("Monitor 4K")).toBeInTheDocument();
    expect(within(article as HTMLElement).getByText("-33%")).toBeInTheDocument();
    expect(within(article as HTMLElement).getByText("PcComponentes")).toBeInTheDocument();
    for (const button of article.querySelectorAll("button")) expect(button).toBeDisabled();
    expect(screen.getByRole("figure", { name: /vista previa/i })).toBeInTheDocument();
  });

  it("sin precio muestra un marcador en vez de 0 €", () => {
    const { container } = render(
      <SubmissionPreviewCard
        title=""
        currentPrice={null}
        previousPrice={null}
        images={[]}
        storeName={null}
      />,
    );
    expect(container.querySelector(".price-now")).toHaveTextContent("— €");
    expect(container.querySelector(".card-title")).toHaveTextContent("Título del chollo");
  });
});
