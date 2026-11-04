import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { emptyForm } from "../deal-form";
import type { useDealImages } from "../hooks/useDealImages";
import { DealFormPanel } from "./DealFormPanel";

const images = {
  uploading: false,
  fileRef: { current: null },
  addImageUrl: vi.fn(),
  handleFiles: vi.fn(),
  removeImage: vi.fn(),
  moveImage: vi.fn(),
} as unknown as ReturnType<typeof useDealImages>;

const validForm = {
  ...emptyForm(),
  title: "Monitor",
  current_price: "100",
  affiliate_url: "https://www.amazon.es/dp/B0ABCDEF12",
};

function renderPanel(extra: Partial<React.ComponentProps<typeof DealFormPanel>> = {}) {
  const props = {
    form: emptyForm(),
    setForm: vi.fn(),
    isEditing: false,
    stores: [],
    cats: [],
    subcats: [],
    images,
    onSubmit: vi.fn((e: React.FormEvent) => e.preventDefault()),
    onCancel: vi.fn(),
    onOpenTelegram: vi.fn(),
    ...extra,
  };
  render(<DealFormPanel {...props} />);
  return props;
}

describe("DealFormPanel", () => {
  it("por defecto mantiene el comportamiento de admin.chollos", async () => {
    const user = userEvent.setup();
    const props = renderPanel();
    expect(screen.getByText("Nuevo chollo")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "GUARDAR" })).toHaveAttribute("type", "submit");
    await user.click(screen.getByRole("button", { name: /Publicar en Telegram/ }));
    expect(props.onOpenTelegram).toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "CANCELAR" }));
    expect(props.onCancel).toHaveBeenCalled();
  });

  it("al editar muestra «Editar chollo»", () => {
    renderPanel({ isEditing: true });
    expect(screen.getByText("Editar chollo")).toBeInTheDocument();
  });

  it("acepta cabecera, texto del botón, pie y acciones extra opcionales", () => {
    renderPanel({
      heading: "Revisar y publicar",
      submitLabel: "Aprobar y publicar",
      showTelegramButton: false,
      footer: <p>pie</p>,
      extraActions: <button type="button">Rechazar</button>,
    });
    expect(screen.getByText("Revisar y publicar")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Aprobar y publicar" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Publicar en Telegram/ })).not.toBeInTheDocument();
    expect(screen.getByText("pie")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Rechazar" })).toBeInTheDocument();
  });

  it("submitDisabled desactiva el botón de envío (por defecto activo)", () => {
    renderPanel({ submitDisabled: true });
    expect(screen.getByRole("button", { name: "GUARDAR" })).toBeDisabled();
  });

  it("por defecto Enter en un input envía el formulario (admin.chollos)", async () => {
    const user = userEvent.setup();
    const props = renderPanel({ form: validForm });
    await user.type(screen.getByPlaceholderText("Título *"), "x{Enter}");
    expect(props.onSubmit).toHaveBeenCalledTimes(1);
  });

  it("preventImplicitSubmit: Enter en un input no envía, el botón sí", async () => {
    const user = userEvent.setup();
    const props = renderPanel({ form: validForm, preventImplicitSubmit: true });
    await user.type(screen.getByPlaceholderText("Título *"), "x{Enter}");
    await user.type(screen.getByPlaceholderText("Enlace afiliado *"), "y{Enter}");
    expect(props.onSubmit).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "GUARDAR" }));
    expect(props.onSubmit).toHaveBeenCalledTimes(1);
  });
});
