import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { CouponCode } from "./CouponCode";

const mocks = vi.hoisted(() => ({ success: vi.fn(), error: vi.fn() }));
vi.mock("sonner", () => ({ toast: { success: mocks.success, error: mocks.error } }));

function setClipboard(writeText: unknown) {
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
}

beforeEach(() => vi.clearAllMocks());
afterEach(() => {
  Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
});

describe("CouponCode", () => {
  it("no renderiza sin código", () => {
    const { container } = render(<CouponCode code={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("copia el código y avisa", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    setClipboard(writeText);
    render(<CouponCode code="SONY10" />);

    expect(screen.getByText("SONY10")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /copiar/i }));

    expect(writeText).toHaveBeenCalledWith("SONY10");
    expect(mocks.success).toHaveBeenCalledWith("Código copiado");
  });

  it("avisa si el portapapeles falla", async () => {
    setClipboard(vi.fn().mockRejectedValue(new Error("denied")));
    render(<CouponCode code="SONY10" />);
    await userEvent.click(screen.getByRole("button", { name: /copiar/i }));

    expect(mocks.error).toHaveBeenCalled();
    expect(mocks.success).not.toHaveBeenCalled();
  });

  it("avisa si no hay API de portapapeles", async () => {
    render(<CouponCode code="SONY10" />);
    await userEvent.click(screen.getByRole("button", { name: /copiar/i }));
    expect(mocks.error).toHaveBeenCalled();
  });
});
