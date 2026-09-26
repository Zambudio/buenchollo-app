import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { isAnalyticsExcluded } from "@/features/analytics/lib/tracking";
import { AnalyticsPreferenceButton } from "./AnalyticsPreferenceButton";

describe("AnalyticsPreferenceButton", () => {
  beforeEach(() => window.localStorage.clear());

  it("permite excluir y volver a incluir el navegador", () => {
    render(<AnalyticsPreferenceButton />);

    fireEvent.click(screen.getByRole("button", { name: "Excluir este dispositivo" }));
    expect(isAnalyticsExcluded(window.localStorage)).toBe(true);
    expect(
      screen.getByText("La medición está desactivada en este dispositivo."),
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Volver a activar la medición" }));
    expect(isAnalyticsExcluded(window.localStorage)).toBe(false);
  });
});
