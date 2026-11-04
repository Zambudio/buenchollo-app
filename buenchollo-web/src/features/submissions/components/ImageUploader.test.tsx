import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { ImageUploader, type ImageUploaderState } from "./ImageUploader";
import { ApiError } from "@/services/api/client";

const mocks = vi.hoisted(() => ({
  uploadImage: vi.fn(),
  importImageUrl: vi.fn(),
  toastError: vi.fn(),
  toastInfo: vi.fn(),
}));

vi.mock("@/services/api/submissions", async (orig) => ({
  ...(await orig<typeof import("@/services/api/submissions")>()),
  submissionsApi: { uploadImage: mocks.uploadImage, importImageUrl: mocks.importImageUrl },
}));
vi.mock("sonner", () => ({ toast: { error: mocks.toastError, info: mocks.toastInfo } }));

const createObjectURL = vi.fn((_: Blob) => "blob:preview");
const revokeObjectURL = vi.fn();
const original = { create: URL.createObjectURL, revoke: URL.revokeObjectURL };

beforeAll(() => {
  URL.createObjectURL = createObjectURL;
  URL.revokeObjectURL = revokeObjectURL;
});
afterAll(() => {
  URL.createObjectURL = original.create;
  URL.revokeObjectURL = original.revoke;
});

beforeEach(() => {
  vi.clearAllMocks();
  let n = 0;
  mocks.uploadImage.mockImplementation(async () => ({
    url: `https://cdn.bc/u${++n}.webp`,
    width: 1,
    height: 1,
  }));
  mocks.importImageUrl.mockImplementation(async (url: string) => ({
    url: `https://cdn.bc/imported-${url.split("/").pop()}`,
    width: 1,
    height: 1,
  }));
});

const png = (name = "a.png", size = 10) =>
  new File([new Uint8Array(size)], name, { type: "image/png" });

function paste(data: Record<string, string>, files: File[] = []) {
  const ev = new Event("paste", { bubbles: true, cancelable: true });
  Object.defineProperty(ev, "clipboardData", {
    value: {
      files,
      items: [],
      types: Object.keys(data),
      getData: (t: string) => data[t] ?? "",
    },
  });
  act(() => {
    (document.activeElement ?? document.body).dispatchEvent(ev);
  });
  return ev;
}

function setup(initial: string[] = []) {
  const onChange = vi.fn<(s: ImageUploaderState) => void>();
  render(<ImageUploader initial={initial} onChange={onChange} />);
  const last = () => onChange.mock.calls.at(-1)![0];
  return { onChange, last };
}

describe("ImageUploader", () => {
  it("muestra el texto de ayuda y el selector de ficheros", () => {
    setup();
    expect(screen.getByText("Arrastra, pega (Ctrl+V) o elige imágenes")).toBeInTheDocument();
    const input = screen.getByLabelText("Elegir imágenes");
    expect(input).toHaveAttribute("type", "file");
    expect(input).toHaveAttribute("accept", "image/*");
    expect(input).toHaveAttribute("multiple");
  });

  it("emite las imágenes precargadas como hechas sin subir nada", () => {
    const { last } = setup([
      "https://m.media-amazon.com/a.jpg",
      "https://m.media-amazon.com/b.jpg",
    ]);
    expect(last()).toEqual({
      images: ["https://m.media-amazon.com/a.jpg", "https://m.media-amazon.com/b.jpg"],
      cover: "https://m.media-amazon.com/a.jpg",
      isUploading: false,
      hasErrors: false,
    });
    expect(mocks.uploadImage).not.toHaveBeenCalled();
  });

  it("pegar una imagen llama a uploadImage y la emite", async () => {
    const { last } = setup();
    const file = png();
    const ev = paste({}, [file]);
    expect(ev.defaultPrevented).toBe(true);
    expect(mocks.uploadImage).toHaveBeenCalledWith(file, "a.png");
    await waitFor(() => expect(last().images).toEqual(["https://cdn.bc/u1.webp"]));
    expect(last().isUploading).toBe(false);
  });

  it("pegar una URL llama a importImageUrl", async () => {
    const { last } = setup();
    paste({ "text/plain": "https://tienda.es/foto.jpg" });
    expect(mocks.importImageUrl).toHaveBeenCalledWith("https://tienda.es/foto.jpg");
    await waitFor(() => expect(last().images).toEqual(["https://cdn.bc/imported-foto.jpg"]));
  });

  it("no intercepta texto normal ni el pegado de texto en un input", () => {
    render(
      <>
        <input aria-label="titulo" />
        <ImageUploader onChange={vi.fn()} />
      </>,
    );
    expect(paste({ "text/plain": "hola" }).defaultPrevented).toBe(false);
    screen.getByLabelText("titulo").focus();
    const ev = paste({ "text/plain": "https://tienda.es/foto.jpg" }, [png()]);
    expect(ev.defaultPrevented).toBe(false);
    expect(mocks.uploadImage).not.toHaveBeenCalled();
    expect(mocks.importImageUrl).not.toHaveBeenCalled();
  });

  it("con foco en un input pero solo imagen en el portapapeles, la sube", () => {
    render(
      <>
        <input aria-label="titulo" />
        <ImageUploader onChange={vi.fn()} />
      </>,
    );
    screen.getByLabelText("titulo").focus();
    paste({}, [png()]);
    expect(mocks.uploadImage).toHaveBeenCalledTimes(1);
  });

  it("la 9ª imagen muestra toast y no se sube", async () => {
    const initial = Array.from({ length: 7 }, (_, i) => `https://m.media-amazon.com/${i}.jpg`);
    const { last } = setup(initial);
    paste({}, [png("8.png"), png("9.png")]);
    expect(mocks.uploadImage).toHaveBeenCalledTimes(1);
    expect(mocks.toastError).toHaveBeenCalledWith(expect.stringMatching(/máximo 8/i));
    await waitFor(() => expect(last().images).toHaveLength(8));
    paste({}, [png("10.png")]);
    expect(mocks.uploadImage).toHaveBeenCalledTimes(1);
  });

  it("rechaza en cliente los ficheros de más de 5 MB", () => {
    setup();
    paste({}, [png("grande.png", 5 * 1024 * 1024 + 1)]);
    expect(mocks.uploadImage).not.toHaveBeenCalled();
    expect(mocks.toastError).toHaveBeenCalledWith(expect.stringMatching(/5 MB/));
  });

  it("limita a 3 subidas simultáneas", async () => {
    const pending: Array<() => void> = [];
    mocks.uploadImage.mockImplementation(
      () =>
        new Promise((resolve) => {
          pending.push(() => resolve({ url: `https://cdn.bc/${pending.length}.webp` }));
        }),
    );
    setup();
    paste({}, [png("1.png"), png("2.png"), png("3.png"), png("4.png")]);
    expect(mocks.uploadImage).toHaveBeenCalledTimes(3);
    await act(async () => pending[0]!());
    await waitFor(() => expect(mocks.uploadImage).toHaveBeenCalledTimes(4));
  });

  it("muestra el error de subida y bloquea el envío hasta quitarla", async () => {
    mocks.uploadImage.mockRejectedValue(new ApiError(400, "No es una imagen válida", null));
    const { last } = setup();
    paste({}, [png()]);
    expect(await screen.findByText("No es una imagen válida")).toBeInTheDocument();
    expect(last().hasErrors).toBe(true);
    await userEvent.click(screen.getByRole("button", { name: "Quitar imagen" }));
    expect(last().hasErrors).toBe(false);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview");
  });

  it("reordenar y portada cambian el orden emitido", async () => {
    const a = "https://m.media-amazon.com/a.jpg";
    const b = "https://m.media-amazon.com/b.jpg";
    const c = "https://m.media-amazon.com/c.jpg";
    const { last } = setup([a, b, c]);
    const user = userEvent.setup();

    await user.click(screen.getAllByRole("button", { name: "Mover a la derecha" })[0]!);
    expect(last().images).toEqual([b, a, c]);
    expect(last().cover).toBe(b);

    await user.click(screen.getAllByRole("button", { name: "Usar como portada" })[2]!);
    expect(last().images).toEqual([c, b, a]);
    expect(last().cover).toBe(c);

    await user.click(screen.getAllByRole("button", { name: "Mover a la izquierda" })[2]!);
    expect(last().images).toEqual([c, a, b]);
  });

  it("añade por URL con el botón Añadir", async () => {
    const { last } = setup();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/imagen por url/i), "https://x.es/y.png");
    await user.click(screen.getByRole("button", { name: "Añadir" }));
    await waitFor(() => expect(last().images).toEqual(["https://cdn.bc/imported-y.png"]));
  });

  it("acepta imágenes soltadas en la zona", async () => {
    const { last } = setup();
    const file = png("drop.png");
    fireEvent.drop(screen.getByTestId("image-dropzone"), {
      dataTransfer: { files: [file], items: [], types: ["Files"], getData: () => "" },
    });
    expect(mocks.uploadImage).toHaveBeenCalledWith(file, "drop.png");
    await waitFor(() => expect(last().images).toHaveLength(1));
  });

  it("botón Pegar solo si existe navigator.clipboard.read y lee imágenes", async () => {
    // user-event instala su propio stub de clipboard: partimos de "no soportado".
    Object.defineProperty(navigator, "clipboard", { value: undefined, configurable: true });
    const { unmount } = render(<ImageUploader onChange={vi.fn()} />);
    expect(screen.queryByRole("button", { name: "Pegar" })).not.toBeInTheDocument();
    unmount();

    const blob = new Blob(["x"], { type: "image/png" });
    const read = vi
      .fn()
      .mockResolvedValue([{ types: ["image/png"], getType: vi.fn().mockResolvedValue(blob) }]);
    Object.defineProperty(navigator, "clipboard", { value: { read }, configurable: true });
    try {
      render(<ImageUploader onChange={vi.fn()} />);
      await userEvent.click(await screen.findByRole("button", { name: "Pegar" }));
      await waitFor(() => expect(mocks.uploadImage).toHaveBeenCalledTimes(1));

      read.mockRejectedValueOnce(new DOMException("denied", "NotAllowedError"));
      await userEvent.click(screen.getByRole("button", { name: "Pegar" }));
      await waitFor(() =>
        expect(mocks.toastError).toHaveBeenCalledWith(expect.stringMatching(/portapapeles/)),
      );
    } finally {
      Reflect.deleteProperty(navigator, "clipboard");
    }
  });
  it("Reintentar vuelve a lanzar la misma subida", async () => {
    mocks.uploadImage
      .mockRejectedValueOnce(new ApiError(503, "caído", null))
      .mockResolvedValueOnce({ url: "https://cdn.bc/ok.webp", width: 1, height: 1 });
    const { last } = setup();
    const file = png("r.png");
    paste({}, [file]);
    const retry = await screen.findByRole("button", { name: "Reintentar" });
    await userEvent.click(retry);
    expect(mocks.uploadImage).toHaveBeenCalledTimes(2);
    expect(mocks.uploadImage.mock.calls[1]).toEqual([file, "r.png"]);
    await waitFor(() => expect(last().images).toEqual(["https://cdn.bc/ok.webp"]));
    expect(last().hasErrors).toBe(false);
  });

  it("Reintentar una URL vuelve a llamar a importImageUrl", async () => {
    mocks.importImageUrl.mockRejectedValueOnce(new ApiError(400, "No es una imagen", null));
    setup();
    paste({ "text/plain": "https://x.es/z.png" });
    await userEvent.click(await screen.findByRole("button", { name: "Reintentar" }));
    expect(mocks.importImageUrl).toHaveBeenCalledTimes(2);
    expect(mocks.importImageUrl).toHaveBeenLastCalledWith("https://x.es/z.png");
  });

  it("una subida que falla tras quitar la imagen no anuncia error", async () => {
    let reject: (e: unknown) => void = () => {};
    mocks.uploadImage.mockReturnValue(new Promise((_, r) => (reject = r)));
    const { container } = render(<ImageUploader onChange={vi.fn()} />);
    paste({}, [png()]);
    await userEvent.click(screen.getByRole("button", { name: "Quitar imagen" }));
    await act(async () => reject(new ApiError(400, "mal", null)));
    const live = container.querySelector('[aria-live="polite"]')!;
    expect(live.textContent).not.toMatch(/no se pudo/i);
    expect(screen.queryAllByTestId("image-item")).toHaveLength(0);
  });

  it("un drop fuera de la zona se previene y añade las imágenes", async () => {
    const { last } = setup();
    const file = png("fuera.png");
    const over = new Event("dragover", { bubbles: true, cancelable: true });
    document.body.dispatchEvent(over);
    expect(over.defaultPrevented).toBe(true);
    const drop = new Event("drop", { bubbles: true, cancelable: true });
    Object.defineProperty(drop, "dataTransfer", {
      value: { files: [file], items: [], types: ["Files"], getData: () => "" },
    });
    act(() => {
      document.body.dispatchEvent(drop);
    });
    expect(drop.defaultPrevented).toBe(true);
    expect(mocks.uploadImage).toHaveBeenCalledWith(file, "fuera.png");
    await waitFor(() => expect(last().images).toHaveLength(1));
  });

  it("en un campo de texto, un drop de ficheros se previene y uno de texto no", () => {
    render(
      <>
        <input aria-label="titulo" />
        <ImageUploader onChange={vi.fn()} />
      </>,
    );
    const input = screen.getByLabelText("titulo");
    const dropOn = (dataTransfer: object) => {
      const ev = new Event("drop", { bubbles: true, cancelable: true });
      Object.defineProperty(ev, "dataTransfer", { value: dataTransfer });
      act(() => {
        input.dispatchEvent(ev);
      });
      return ev;
    };
    const overOn = (types: string[]) => {
      const ev = new Event("dragover", { bubbles: true, cancelable: true });
      Object.defineProperty(ev, "dataTransfer", { value: { types } });
      input.dispatchEvent(ev);
      return ev;
    };

    expect(overOn(["text/plain"]).defaultPrevented).toBe(false);
    const textDrop = dropOn({
      files: [],
      items: [],
      types: ["text/plain"],
      getData: (t: string) => (t === "text/plain" ? "https://x.es/a.png" : ""),
    });
    expect(textDrop.defaultPrevented).toBe(false);
    expect(mocks.importImageUrl).not.toHaveBeenCalled();

    expect(overOn(["Files"]).defaultPrevented).toBe(true);
    const file = png("en-input.png");
    const fileDrop = dropOn({ files: [file], items: [], types: ["Files"], getData: () => "" });
    expect(fileDrop.defaultPrevented).toBe(true);
    expect(mocks.uploadImage).toHaveBeenCalledWith(file, "en-input.png");
  });

  it("un drop dentro de la zona no se añade dos veces", () => {
    setup();
    fireEvent.drop(screen.getByTestId("image-dropzone"), {
      dataTransfer: { files: [png()], items: [], types: ["Files"], getData: () => "" },
    });
    expect(mocks.uploadImage).toHaveBeenCalledTimes(1);
  });

  it("al desmontar quita los listeners del documento", () => {
    const { unmount } = render(<ImageUploader onChange={vi.fn()} />);
    unmount();
    const drop = new Event("drop", { bubbles: true, cancelable: true });
    document.body.dispatchEvent(drop);
    expect(drop.defaultPrevented).toBe(false);
    expect(paste({}, [png()]).defaultPrevented).toBe(false);
  });
});
