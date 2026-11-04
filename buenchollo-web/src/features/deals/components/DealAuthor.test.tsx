import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DealAuthor } from "./DealAuthor";

describe("DealAuthor", () => {
  it("no renderiza nada sin autor", () => {
    const { container } = render(<DealAuthor author={null} size="sm" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("muestra display_name y avatar sin referrer", () => {
    const { container } = render(
      <DealAuthor
        size="md"
        author={{ username: "pepe", display_name: "Pepe G", avatar_url: "https://a.test/p.png" }}
      />,
    );
    expect(screen.getByText("Pepe G")).toBeInTheDocument();
    expect(screen.getByText(/Compartido por/)).toBeInTheDocument();
    const img = container.querySelector("img")!;
    expect(img).toHaveAttribute("referrerpolicy", "no-referrer");
  });

  it("usa username si no hay display_name y la inicial si no hay avatar", () => {
    render(
      <DealAuthor size="sm" author={{ username: "pepe", display_name: null, avatar_url: null }} />,
    );
    expect(screen.getByText("pepe")).toBeInTheDocument();
    expect(screen.getByTestId("author-initial")).toHaveTextContent("p");
  });

  it("cae a la inicial si el avatar falla al cargar", () => {
    const { container } = render(
      <DealAuthor
        size="sm"
        author={{ username: "ana", display_name: null, avatar_url: "https://a.test/x.png" }}
      />,
    );
    fireEvent.error(container.querySelector("img")!);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByTestId("author-initial")).toBeInTheDocument();
  });
});
