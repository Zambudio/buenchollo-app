import { Info } from "lucide-react";

/** Declaración automática de afiliación: se muestra siempre que el artículo
 * contenga al menos un bloque de producto recomendado (`has_affiliate_links`
 * calculado por el backend). No depende de que el admin la escriba a mano. */
export function AffiliateDisclosure() {
  return (
    <div className="not-prose flex items-start gap-2 border border-surface-700 bg-surface-800/50 rounded px-3 py-2 text-xs text-muted-foreground mb-6">
      <Info className="size-4 shrink-0 mt-0.5" />
      <p>
        Este artículo contiene enlaces de afiliado. Si compras a través de ellos, podemos recibir
        una comisión sin coste adicional para ti.
      </p>
    </div>
  );
}
