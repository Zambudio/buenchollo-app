import Color from "@tiptap/extension-color";
import { nearestAllowedColor } from "@/features/blog/utils/textColors";

/** Extiende el Color oficial de Tiptap para que, al pegar contenido con
 * colores arbitrarios (p. ej. copiado de un chat de IA), el color se ajuste
 * al de la paleta permitida más cercano en vez de aceptarse tal cual — el
 * backend rechazaría cualquier color fuera de esa paleta al guardar. */
export const BlogColor = Color.extend({
  addGlobalAttributes() {
    return [
      {
        types: this.options.types,
        attributes: {
          color: {
            default: null,
            parseHTML: (element: HTMLElement) => nearestAllowedColor(element.style.color),
            renderHTML: (attributes: { color?: string | null }) => {
              if (!attributes.color) return {};
              return { style: `color: ${attributes.color}` };
            },
          },
        },
      },
    ];
  },
});
