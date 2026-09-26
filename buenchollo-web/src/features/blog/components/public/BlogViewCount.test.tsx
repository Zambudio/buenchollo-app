import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { BlogViewCount } from "./BlogViewCount";

describe("BlogViewCount", () => {
  it("muestra el contador validado con formato español y etiqueta accesible", () => {
    render(<BlogViewCount count={1284} />);

    expect(screen.getByLabelText("1.284 visualizaciones validadas")).toBeInTheDocument();
    expect(screen.getByText("1.284 visitas")).toBeInTheDocument();
  });

  it("muestra cero durante un despliegue en el que la API antigua aún no envía el contador", () => {
    render(<BlogViewCount count={undefined} />);

    expect(screen.getByText("0 visitas")).toBeInTheDocument();
  });
});
