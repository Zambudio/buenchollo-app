/** Compartido entre el editor (extensions/callout.tsx) y el renderer público
 * (components/public/ContentRenderer.tsx) — vive fuera de ambos para que la
 * parte pública no arrastre código del editor Tiptap en su bundle. */
export const CALLOUT_VARIANTS = [
  { value: "info", label: "Información" },
  { value: "tip", label: "Consejo" },
  { value: "warning", label: "Advertencia" },
  { value: "verdict", label: "Veredicto" },
] as const;
