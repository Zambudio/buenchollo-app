import { mergeAttributes, Node } from "@tiptap/core";
import { NodeViewWrapper, ReactNodeViewRenderer } from "@tiptap/react";
import type { NodeViewProps } from "@tiptap/react";
import { useState } from "react";
import { Trash2, Search } from "lucide-react";
import { dealsService } from "@/services/api/deals";
import type { DealCardData } from "@/features/deals/components/DealCard";
import { isAllowedAffiliateDomain } from "@/features/blog/utils/affiliateDomains";
import { useBlogImages } from "@/features/blog/hooks/useBlogImages";
import { useAuth } from "@/hooks/useAuth";

export interface ProductRecommendationAttrs {
  mode: "deal" | "manual";
  deal_id: string | null;
  name: string | null;
  image_url: string | null;
  affiliate_url: string | null;
  note: string | null;
  button_text: string | null;
  badge: string | null;
}

function ProductBlockView({ node, updateAttributes, deleteNode, editor }: NodeViewProps) {
  const attrs = node.attrs as ProductRecommendationAttrs;
  const { user } = useAuth();
  const { uploadImage, uploading } = useBlogImages(user?.id, "shared");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<DealCardData[]>([]);
  const [searching, setSearching] = useState(false);
  const editable = editor.isEditable;

  const runSearch = async () => {
    if (!query.trim()) return;
    setSearching(true);
    try {
      const found = await dealsService.search({ search: query.trim(), limit: 8 });
      setResults(found);
    } finally {
      setSearching(false);
    }
  };

  const pickDeal = (deal: DealCardData) => {
    updateAttributes({
      mode: "deal",
      deal_id: deal.id,
      name: deal.title,
      image_url: deal.image_url,
      affiliate_url: deal.affiliate_url ?? null,
    });
    setResults([]);
    setQuery("");
  };

  const affiliateUrlInvalid =
    attrs.mode === "manual" &&
    !!attrs.affiliate_url &&
    !isAllowedAffiliateDomain(attrs.affiliate_url);

  if (!editable) {
    // Vista de solo lectura dentro del editor (p.ej. al previsualizar contenido embebido)
    return (
      <NodeViewWrapper className="my-3 border border-surface-700 rounded p-3 bg-surface-800/40">
        <p className="text-sm font-bold">{attrs.name || "Producto sin configurar"}</p>
      </NodeViewWrapper>
    );
  }

  return (
    <NodeViewWrapper
      contentEditable={false}
      className="my-3 border border-surface-700 rounded p-3 bg-surface-800/40 space-y-3"
      data-drag-handle
    >
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => updateAttributes({ mode: "deal" })}
            className={`text-xs font-mono uppercase px-2 py-1 border ${attrs.mode === "deal" ? "bg-cyan-glow text-surface-900 border-cyan-glow" : "border-surface-700"}`}
          >
            Chollo existente
          </button>
          <button
            type="button"
            onClick={() => updateAttributes({ mode: "manual" })}
            className={`text-xs font-mono uppercase px-2 py-1 border ${attrs.mode === "manual" ? "bg-cyan-glow text-surface-900 border-cyan-glow" : "border-surface-700"}`}
          >
            Producto manual
          </button>
        </div>
        <button
          type="button"
          aria-label="Eliminar bloque de producto"
          onClick={() => deleteNode()}
          className="text-red-400 hover:text-red-300"
        >
          <Trash2 className="size-4" />
        </button>
      </div>

      {attrs.mode === "deal" ? (
        <div className="space-y-2">
          <div className="flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && (e.preventDefault(), runSearch())}
              placeholder="Buscar chollo por título..."
              className="flex-1 bg-surface-900 border border-surface-700 px-2 py-1 text-sm outline-none focus:border-cyan-glow"
              aria-label="Buscar chollo existente"
            />
            <button
              type="button"
              onClick={runSearch}
              className="border border-surface-700 px-2 py-1"
              aria-label="Buscar"
            >
              <Search className="size-4" />
            </button>
          </div>
          {searching && <p className="text-xs text-muted-foreground">Buscando...</p>}
          {results.length > 0 && (
            <ul className="border border-surface-700 divide-y divide-surface-700 max-h-40 overflow-y-auto">
              {results.map((deal) => (
                <li key={deal.id}>
                  <button
                    type="button"
                    onClick={() => pickDeal(deal)}
                    className="w-full text-left px-2 py-1.5 text-sm hover:bg-surface-700"
                  >
                    {deal.title}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {attrs.deal_id && (
            <p className="text-sm">
              Seleccionado: <strong>{attrs.name}</strong>
            </p>
          )}
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          <input
            value={attrs.name ?? ""}
            onChange={(e) => updateAttributes({ name: e.target.value })}
            placeholder="Nombre del producto"
            className="bg-surface-900 border border-surface-700 px-2 py-1 text-sm outline-none focus:border-cyan-glow sm:col-span-2"
            aria-label="Nombre del producto"
          />
          <input
            value={attrs.affiliate_url ?? ""}
            onChange={(e) => updateAttributes({ affiliate_url: e.target.value })}
            placeholder="https://... URL de afiliado"
            className={`bg-surface-900 border px-2 py-1 text-sm outline-none sm:col-span-2 ${affiliateUrlInvalid ? "border-red-500" : "border-surface-700 focus:border-cyan-glow"}`}
            aria-label="URL de afiliado"
          />
          {affiliateUrlInvalid && (
            <p className="text-xs text-red-400 sm:col-span-2">
              Dominio no permitido para enlaces de afiliado.
            </p>
          )}
          <div className="sm:col-span-2 flex items-center gap-2">
            {attrs.image_url && (
              <img src={attrs.image_url} alt="" className="size-12 object-cover rounded" />
            )}
            <label className="text-xs font-mono uppercase border border-surface-700 px-2 py-1 cursor-pointer">
              {uploading ? "Subiendo..." : "Subir imagen"}
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/avif"
                className="hidden"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  const url = await uploadImage(file);
                  if (url) updateAttributes({ image_url: url });
                }}
              />
            </label>
          </div>
        </div>
      )}

      <div className="grid gap-2 sm:grid-cols-2">
        <input
          value={attrs.note ?? ""}
          onChange={(e) => updateAttributes({ note: e.target.value })}
          placeholder="Recomendación editorial corta"
          maxLength={600}
          className="bg-surface-900 border border-surface-700 px-2 py-1 text-sm outline-none focus:border-cyan-glow sm:col-span-2"
          aria-label="Recomendación editorial"
        />
        <input
          value={attrs.button_text ?? ""}
          onChange={(e) => updateAttributes({ button_text: e.target.value })}
          placeholder="Texto del botón (p.ej. Ver oferta)"
          maxLength={60}
          className="bg-surface-900 border border-surface-700 px-2 py-1 text-sm outline-none focus:border-cyan-glow"
          aria-label="Texto del botón"
        />
        <input
          value={attrs.badge ?? ""}
          onChange={(e) => updateAttributes({ badge: e.target.value })}
          placeholder="Etiqueta (opcional, p.ej. Nuestra elección)"
          maxLength={40}
          className="bg-surface-900 border border-surface-700 px-2 py-1 text-sm outline-none focus:border-cyan-glow"
          aria-label="Etiqueta del producto"
        />
      </div>
    </NodeViewWrapper>
  );
}

export const ProductRecommendation = Node.create({
  name: "productRecommendation",
  group: "block",
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      mode: { default: "manual" },
      deal_id: { default: null },
      name: { default: null },
      image_url: { default: null },
      affiliate_url: { default: null },
      note: { default: null },
      button_text: { default: null },
      badge: { default: null },
    };
  },

  parseHTML() {
    return [{ tag: "div[data-product-recommendation]" }];
  },

  renderHTML({ HTMLAttributes }) {
    return ["div", mergeAttributes(HTMLAttributes, { "data-product-recommendation": "" })];
  },

  addNodeView() {
    return ReactNodeViewRenderer(ProductBlockView);
  },
});
