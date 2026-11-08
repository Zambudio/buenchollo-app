// FIXTURES sintéticas: ningún dato corresponde a un producto real.
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { AffiliateImportPanel } from "./AffiliateImportPanel";
import type { ImportResponse } from "@/services/api/affiliates";

const base: ImportResponse = {
  status: "ambiguous",
  message: "Varias variantes coinciden: elige la correcta.",
  stage: "link_generated",
  program: {
    id: "p1",
    name: "PcComponentes",
    network: "awin",
    advertiser_id: "20982",
    membership_status: "joined",
    membership_checked_at: null,
    enabled: true,
    disclosure_text: null,
    image_channels: [],
    max_data_age_hours: 24,
    store_id: null,
  },
  program_options: [],
  link: {
    status: "generated",
    affiliate_url: "https://www.awin1.com/x",
    source: "awin_linkbuilder",
  },
  offer: null,
  provenance: null,
  missing: [],
  candidates: [
    {
      product_key: "F-2001",
      title: "FIXTURE SSD 1TB",
      price: "59.99",
      colour: "Negro",
      condition: "new",
      ean: null,
      sku: null,
      url: null,
      image_url: null,
    },
    {
      product_key: "F-2002",
      title: "FIXTURE SSD 1TB Reacondicionado",
      price: "44.99",
      colour: "Negro",
      condition: "refurbished",
      ean: null,
      sku: null,
      url: null,
      image_url: null,
    },
  ],
  existing_deal: null,
  warnings: [],
};

function renderPanel(result: ImportResponse, onChooseCandidate = vi.fn()) {
  render(
    <AffiliateImportPanel
      result={result}
      conflicts={[]}
      ready={false}
      busy={false}
      onChooseProgram={vi.fn()}
      onChooseCandidate={onChooseCandidate}
      onSearchIds={vi.fn()}
      onResolveConflict={vi.fn()}
      onOpenExisting={vi.fn()}
      onDismiss={vi.fn()}
    />,
  );
}

describe("AffiliateImportPanel", () => {
  it("distingue enlace generado de producto importado y de lista para publicar", () => {
    renderPanel(base);
    expect(screen.getByText("Coincidencia ambigua")).toBeInTheDocument();
    const steps = screen.getByRole("list", { name: "Etapas" });
    expect(steps).toHaveTextContent("Enlace generado");
    expect(steps).toHaveTextContent("Producto importado");
    expect(steps).toHaveTextContent("Lista para publicar");
  });

  it("no elige variante: el usuario la selecciona", () => {
    const choose = vi.fn();
    renderPanel(base, choose);
    expect(choose).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: /Reacondicionado/ }));
    expect(choose).toHaveBeenCalledWith("F-2002");
  });

  it("muestra el estado pendiente de aprobación", () => {
    renderPanel({
      ...base,
      status: "pending_approval",
      message: "Programa no aprobado (estado: pending).",
      link: { status: "not_requested" },
      candidates: [],
      program: { ...base.program!, membership_status: "pending" },
    });
    expect(screen.getByText("Pendiente de aprobación")).toBeInTheDocument();
    expect(screen.getByText(/Adhesión:/)).toHaveTextContent("pending");
  });
});
