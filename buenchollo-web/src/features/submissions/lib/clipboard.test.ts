import { describe, expect, it } from "vitest";
import { extractClipboardItems, hasPlainText, isTextEntryElement } from "./clipboard";

function dataTransfer(
  data: Record<string, string> = {},
  files: File[] = [],
  items: { kind: string; type: string; getAsFile: () => File | null }[] = [],
): DataTransfer {
  return {
    files,
    items,
    types: [...Object.keys(data), ...(files.length ? ["Files"] : [])],
    getData: (type: string) => data[type] ?? "",
  } as unknown as DataTransfer;
}

function pasteEvent(dt: DataTransfer): ClipboardEvent {
  const ev = new Event("paste") as ClipboardEvent;
  Object.defineProperty(ev, "clipboardData", { value: dt });
  return ev;
}

const png = () => new File(["x"], "captura.png", { type: "image/png" });

describe("extractClipboardItems", () => {
  it("devuelve los ficheros de imagen", () => {
    const file = png();
    const out = extractClipboardItems(pasteEvent(dataTransfer({}, [file])));
    expect(out).toEqual({ files: [file], urls: [] });
  });

  it("ignora ficheros que no son imagen", () => {
    const pdf = new File(["x"], "a.pdf", { type: "application/pdf" });
    expect(extractClipboardItems(dataTransfer({}, [pdf]))).toEqual({ files: [], urls: [] });
  });

  it("usa items de tipo file si files viene vacío", () => {
    const file = png();
    const out = extractClipboardItems(
      dataTransfer({}, [], [{ kind: "file", type: "image/png", getAsFile: () => file }]),
    );
    expect(out.files).toEqual([file]);
  });

  it("con HTML extrae los src http(s) de los <img>", () => {
    const html =
      '<p>hola</p><img src="https://x/y.jpg"><img src="data:image/png;base64,AAA"><img src="javascript:alert(1)">';
    const out = extractClipboardItems(dataTransfer({ "text/html": html }));
    expect(out).toEqual({ files: [], urls: ["https://x/y.jpg"] });
  });

  it("con una URL en texto plano la devuelve", () => {
    const out = extractClipboardItems(dataTransfer({ "text/plain": "  https://img.es/a.webp \n" }));
    expect(out).toEqual({ files: [], urls: ["https://img.es/a.webp"] });
  });

  it("con text/uri-list (arrastrar) devuelve las URL sin comentarios", () => {
    const out = extractClipboardItems(
      dataTransfer({ "text/uri-list": "# comentario\r\nhttps://a.es/1.png\r\nhttps://a.es/2.png" }),
    );
    expect(out.urls).toEqual(["https://a.es/1.png", "https://a.es/2.png"]);
  });

  it("con texto normal no devuelve nada", () => {
    expect(extractClipboardItems(dataTransfer({ "text/plain": "hola mundo" }))).toEqual({
      files: [],
      urls: [],
    });
  });

  it("no acepta esquemas distintos de http(s)", () => {
    expect(extractClipboardItems(dataTransfer({ "text/plain": "ftp://x/y.png" })).urls).toEqual([]);
  });

  it("si hay ficheros no mira el texto", () => {
    const file = png();
    const out = extractClipboardItems(dataTransfer({ "text/plain": "https://a.es/x.png" }, [file]));
    expect(out).toEqual({ files: [file], urls: [] });
  });

  it("sin clipboardData devuelve vacío", () => {
    expect(extractClipboardItems(new Event("paste") as ClipboardEvent)).toEqual({
      files: [],
      urls: [],
    });
  });
});

describe("hasPlainText", () => {
  it("detecta texto no vacío", () => {
    expect(hasPlainText(pasteEvent(dataTransfer({ "text/plain": "a" })))).toBe(true);
    expect(hasPlainText(pasteEvent(dataTransfer({ "text/plain": "  " })))).toBe(false);
    expect(hasPlainText(pasteEvent(dataTransfer({}, [png()])))).toBe(false);
  });
});

describe("isTextEntryElement", () => {
  it("reconoce campos de texto", () => {
    const text = document.createElement("input");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    const area = document.createElement("textarea");
    const button = document.createElement("button");
    expect(isTextEntryElement(text)).toBe(true);
    expect(isTextEntryElement(area)).toBe(true);
    expect(isTextEntryElement(checkbox)).toBe(false);
    expect(isTextEntryElement(button)).toBe(false);
    expect(isTextEntryElement(null)).toBe(false);
  });
});
