import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
  }: {
    footerVisible: boolean;
    onToggleFooter: () => void;
  }) => (
    <button type="button" onClick={onToggleFooter}>
      {footerVisible ? "Ocultar pie de página" : "Mostrar pie de página"}
    </button>
  ),
}));

beforeEach(() => {
  Object.defineProperty(window, "scrollY", { configurable: true, value: 0 });
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => {
    callback(0);
    return 1;
  });
  vi.spyOn(window, "cancelAnimationFrame").mockImplementation(() => undefined);
});

describe("Layout footer", () => {
  it("muestra y oculta el pie sin desplazar la página", async () => {
    const user = userEvent.setup();
    const scrollTo = vi.spyOn(window, "scrollTo");
    render(<Layout>Contenido</Layout>);

    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Mostrar pie de página" }));
    expect(screen.getByRole("contentinfo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ocultar pie de página" })).toBeInTheDocument();
    expect(scrollTo).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Ocultar pie de página" }));
    expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument();
  });

  it("oculta el pie cuando el usuario hace scroll", async () => {
    const user = userEvent.setup();
    render(<Layout>Contenido</Layout>);
    await user.click(screen.getByRole("button", { name: "Mostrar pie de página" }));

    Object.defineProperty(window, "scrollY", { configurable: true, value: 40 });
    fireEvent.scroll(window);

    await waitFor(() => expect(screen.queryByRole("contentinfo")).not.toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Mostrar pie de página" })).toBeInTheDocument();
  });
});
