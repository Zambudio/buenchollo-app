import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AmazonAutofillPanel } from "./AmazonAutofillPanel";

describe("AmazonAutofillPanel", () => {
  it("renderiza el panel con input, selector de IA y boton de autocompletar", () => {
    const onUrlChange = vi.fn();
    const onProviderChange = vi.fn();
    const onAutofill = vi.fn();

    render(
      <AmazonAutofillPanel
        url="https://amazon.es/dp/B08TEST123"
        busy={false}
        provider="omniroute"
        onUrlChange={onUrlChange}
        onProviderChange={onProviderChange}
        onAutofill={onAutofill}
      />
    );

    expect(screen.getByText(/Autocompletar desde Amazon/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Motor IA/i)).toBeInTheDocument();
    const select = screen.getByLabelText(/Motor IA/i) as HTMLSelectElement;
    expect(select.value).toBe("omniroute");
    expect(screen.getByRole("button", { name: /AUTOCOMPLETAR/i })).toBeInTheDocument();
  });

  it("permite cambiar el motor de IA seleccionado", () => {
    const onProviderChange = vi.fn();

    render(
      <AmazonAutofillPanel
        url=""
        busy={false}
        provider="omniroute"
        onUrlChange={vi.fn()}
        onProviderChange={onProviderChange}
        onAutofill={vi.fn()}
      />
    );

    const select = screen.getByLabelText(/Motor IA/i);
    fireEvent.change(select, { target: { value: "openai" } });
    expect(onProviderChange).toHaveBeenCalledWith("openai");
  });

  it("deshabilita los controles y muestra spinner cuando esta procesando", () => {
    render(
      <AmazonAutofillPanel
        url="https://amazon.es/dp/B08TEST123"
        busy={true}
        provider="openai"
        onUrlChange={vi.fn()}
        onProviderChange={vi.fn()}
        onAutofill={vi.fn()}
      />
    );

    expect(screen.getByText(/PROCESANDO.../i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Motor IA/i)).toBeDisabled();
    expect(screen.getByRole("button", { name: /PROCESANDO.../i })).toBeDisabled();
  });
});
