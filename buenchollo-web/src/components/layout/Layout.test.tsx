import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Layout } from "./Layout";

vi.mock("./Header", () => ({ Header: () => <header>Cabecera</header> }));
vi.mock("./CategoryBar", () => ({ CategoryBar: () => <nav>Categorías</nav> }));
vi.mock("./Footer", () => ({ Footer: () => <footer id="site-footer">Pie de página</footer> }));
vi.mock("./CookieBanner", () => ({ CookieBanner: () => null }));
vi.mock("./ScrollNav", () => ({
  ScrollNav: ({
    footerVisible,
    onToggleFooter,
    showFooterToggle = true,
  }: {
    footerVisible: boolean;
    onToggleFooter: () => void;
    showFooterToggle?: boolean;
  }) => (
    <nav>
      <button type="button">Ir arriba</button>
      {showFooterToggle && (
        <button type="button" onClick={onToggleFooter}>
          {footerVisible ? "Ocultar pie de página" : "Mostrar pie de página"}
        </button>
      )}
    </nav>
  ),
}));

beforeEach(() => {
  Object.defineProperty(window, "scrollY", { configurable: true, value: 0 });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 800 });
  Object.defineProperty(document.documentElement, "scrollHeight", {
    configurable: true,
    value: 1600,
  });
});

describe("Layout footer", () => {
  it("abre el pie como panel sin desplazar la página", async () => {
    const user = userEvent.setup();
    render(<Layout>Contenido</Layout>);

    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Mostrar pie de página" }));
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mostrar pie de página" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ocultar pie de página" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Ocultar pie de página" }));
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("al llegar al pie muestra solamente la acción de volver arriba", () => {
    render(<Layout>Contenido</Layout>);
    Object.defineProperty(window, "scrollY", { configurable: true, value: 800 });
    fireEvent.scroll(window);

    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Mostrar pie de página" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ir arriba" })).toBeInTheDocument();
  });
});
