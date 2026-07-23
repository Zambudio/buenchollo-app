import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AffiliateDisclosure } from "./AffiliateDisclosure";

describe("AffiliateDisclosure", () => {
  it("muestra el texto legal de afiliación", () => {
    render(<AffiliateDisclosure />);
    expect(screen.getByText(/enlaces de afiliado/i)).toBeInTheDocument();
    expect(screen.getByText(/comisión sin coste adicional/i)).toBeInTheDocument();
  });
});
