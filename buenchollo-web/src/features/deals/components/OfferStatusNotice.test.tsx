import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OfferStatusNotice } from "./OfferStatusNotice";

const NOW = new Date("2026-11-05T12:00:00Z");
const hoursAgo = (h: number) => new Date(NOW.getTime() - h * 3_600_000).toISOString();

describe("OfferStatusNotice", () => {
  it("sin oferta y comprobado hace poco: motivo y precio actual", () => {
    render(
      <OfferStatusNotice
        status="expired"
        offerEndReason="price_increase"
        currentPrice={129.9}
        lastPriceCheckAt={hoursAgo(3)}
        storeName="Amazon"
        now={NOW}
      />,
    );
    expect(screen.getByText("Ahora mismo no está en oferta")).toBeInTheDocument();
    expect(screen.getByText(/Ha subido de precio/)).toBeInTheDocument();
    expect(screen.getByText(/Precio actual: 129,90/)).toBeInTheDocument();
    expect(screen.getByText(/comprobado hace 3 h/)).toBeInTheDocument();
  });

  it("sin oferta y precio de Amazon de más de 24 h: no muestra el precio", () => {
    render(
      <OfferStatusNotice
        status="expired"
        offerEndReason="out_of_stock"
        currentPrice={50}
        lastPriceCheckAt={hoursAgo(30)}
        storeName="Amazon"
        now={NOW}
      />,
    );
    expect(screen.getByText(/Agotado/)).toBeInTheDocument();
    expect(screen.queryByText(/Precio actual/)).not.toBeInTheDocument();
    expect(screen.getByText("Ver precio en Amazon")).toBeInTheDocument();
  });

  it("sin oferta por fecha y nunca comprobado: motivo genérico, sin precio", () => {
    render(
      <OfferStatusNotice
        status="expired"
        offerEndReason="expired_date"
        currentPrice={10}
        lastPriceCheckAt={null}
        storeName="PcComponentes"
        now={NOW}
      />,
    );
    expect(screen.getByText(/La oferta ha terminado/)).toBeInTheDocument();
    expect(screen.queryByText(/Precio actual/)).not.toBeInTheDocument();
    expect(screen.queryByText("Ver precio en Amazon")).not.toBeInTheDocument();
  });

  it("activo comprobado hoy: indica cuándo", () => {
    render(
      <OfferStatusNotice
        status="active"
        offerEndReason={null}
        currentPrice={10}
        lastPriceCheckAt={hoursAgo(0.5)}
        storeName="Amazon"
        now={NOW}
      />,
    );
    expect(screen.getByText("Precio comprobado hace menos de 1 h")).toBeInTheDocument();
  });

  it("activo con comprobación antigua: avisa de que puede haber cambiado", () => {
    render(
      <OfferStatusNotice
        status="active"
        offerEndReason={null}
        currentPrice={10}
        lastPriceCheckAt={hoursAgo(50)}
        storeName="Amazon"
        now={NOW}
      />,
    );
    expect(screen.getByText("Precio de hace 2 días: puede haber cambiado")).toBeInTheDocument();
  });

  it("activo sin comprobación o borrador: no renderiza nada", () => {
    const { container, rerender } = render(
      <OfferStatusNotice
        status="active"
        offerEndReason={null}
        currentPrice={1}
        lastPriceCheckAt={null}
        now={NOW}
      />,
    );
    expect(container).toBeEmptyDOMElement();
    rerender(
      <OfferStatusNotice
        status="draft"
        offerEndReason={null}
        currentPrice={1}
        lastPriceCheckAt={hoursAgo(1)}
        now={NOW}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
