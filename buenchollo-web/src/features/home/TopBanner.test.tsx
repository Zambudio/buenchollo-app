import { act, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TopBanner } from "./TopBanner";
import type { BannerTop } from "./bannerTops";
vi.mock("@tanstack/react-router", () => ({
  Link: ({
    to,
    params,
    children,
    ...props
  }: {
    to: string;
    params?: { slug: string };
    children: React.ReactNode;
  }) => (
    <a href={to.replace("$slug", params?.slug ?? "")} {...props}>
      {children}
    </a>
  ),
}));
const tops: BannerTop[] = ["Audio", "Informática"].map((name, i) => ({
  name,
  slug: `category-${i}`,
  products: [1, 2, 3].map((position) => ({
    id: `${i}-${position}`,
    title: `${name} ${position}`,
    position,
    image_url: `/product-${i}-${position}.jpg`,
    vote_count: 0,
    current_price: null,
    deal_slug: null,
    deal_status: null,
  })),
}));
beforeEach(() => {
  vi.stubGlobal(
    "matchMedia",
    vi.fn(() => ({ matches: false, addEventListener: vi.fn(), removeEventListener: vi.fn() })),
  );
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  vi.restoreAllMocks();
});
describe("TopBanner", () => {
  it("navigates complete category podiums without mixing their positions", () => {
    render(<TopBanner tops={tops} />);
    expect(screen.getByRole("link", { name: "Top Audio" })).toHaveAttribute(
      "href",
      "/categoria/category-0",
    );
    expect(screen.getByRole("link", { name: /Puesto 1: Audio 1/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Siguiente top" }));
    expect(screen.getByRole("link", { name: /Puesto 1: Informática 1/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Puesto 1: Audio/ })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Top Informática" })).toBeInTheDocument();
    expect(screen.queryByText("Estrena los votos de este top")).not.toBeInTheDocument();
  });
  it("keeps a useful link when no rankings are available", () => {
    render(<TopBanner tops={[]} />);
    expect(screen.getByRole("link", { name: /Ver tops y votar/ })).toHaveAttribute(
      "href",
      "/categorias",
    );
    expect(screen.queryByRole("button", { name: "Siguiente top" })).not.toBeInTheDocument();
  });
  it("rotates every five seconds and continues after using the arrows", () => {
    vi.useFakeTimers();
    render(<TopBanner tops={tops} />);
    expect(screen.getAllByRole("button")).toHaveLength(2);
    act(() => vi.advanceTimersByTime(4999));
    expect(screen.getByRole("link", { name: "Top Audio" })).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(1));
    expect(screen.getByRole("link", { name: "Top Informática" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Siguiente top" }));
    expect(screen.getByRole("link", { name: "Top Audio" })).toBeInTheDocument();
    act(() => vi.advanceTimersByTime(5000));
    expect(screen.getByRole("link", { name: "Top Informática" })).toBeInTheDocument();
  });
  it("respects reduced motion", () => {
    vi.useFakeTimers();
    vi.spyOn(window, "matchMedia").mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    } as unknown as MediaQueryList);
    render(<TopBanner tops={tops} />);
    act(() => vi.advanceTimersByTime(16000));
    expect(screen.getByRole("link", { name: "Top Audio" })).toBeInTheDocument();
  });
});
