import Image from "@tiptap/extension-image";
import { mergeAttributes } from "@tiptap/core";

/** Extiende la imagen oficial de Tiptap con alineación y ancho (normal/full),
 * únicos atributos adicionales que el backend valida (`domain/content.py`). */
export const BlogImage = Image.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      align: { default: "left" },
      width: { default: "normal" },
    };
  },

  renderHTML({ HTMLAttributes }) {
    const { align, width, ...rest } = HTMLAttributes as Record<string, string>;
    return ["img", mergeAttributes(rest, { "data-align": align, "data-width": width })];
  },
});
